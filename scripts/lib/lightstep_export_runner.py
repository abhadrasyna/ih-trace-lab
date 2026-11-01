"""Per-kind export pipeline and run loop for the daily Lightstep export.

Everything external (transport, tokens, target resolution, the input check, result printing) is injected;
the only composition root is the CLI's ``main()``.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scripts.lib.lightstep_api import (
    LightstepError,
    Project,
    Series,
    Transport,
    fetch_all_series,
    load_token,
    split_window,
    utc_day_window,
)
from scripts.lib.lightstep_csv import FileExistsRefused, write_rows
from scripts.lib.lightstep_export_kinds import (
    SHARED_ONLY,
    ExportTarget,
    KindSpec,
    expand_query,
    expected_columns,
    get_kind,
    output_file_name,
)
from src.lib.logging.redact import redact_params
from src.tenant_registry import TenantConfig

LOGGER = logging.getLogger("scripts.lib.lightstep_export_runner")
ENDPOINTS = {
    "EU": ("https://api.eu.lightstep.com/public/v0.2", "Synamedia-EU"),
    "US": ("https://api.lightstep.com/public/v0.2", "Synamedia"),
}
CORE_KINDS = ("ctap", "smvod", "smvod-ts")
DRM_REQUIRED = ("mdrmfe", "mdrm-lrm")
InputCheck = Callable[[Path, bool], tuple[str, bool]]
TargetResolver = Callable[[str, TenantConfig], ExportTarget]


class TenantSafetyError(ValueError):
    """A shared-project export does not contain exactly the requested tenant."""


class TokenProvider(Protocol):
    def token(self, region: str) -> str: ...


class EnvTokenProvider:
    """Reads ``LIGHTSTEP_API_KEY_<REGION>`` from the environment or the gitignored ``.env``, once per region."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def token(self, region: str) -> str:
        key = region.upper()
        if key not in self._tokens:
            self._tokens[key] = load_token(key)
        return self._tokens[key]


@dataclass(frozen=True)
class Dependencies:
    transport: Transport
    tokens: TokenProvider
    resolve_target: TargetResolver
    input_check: InputCheck
    report: Callable[[Sequence["KindResult"], str | None], None]


@dataclass(frozen=True)
class ExportRequest:
    tenant: TenantConfig
    day: str
    kinds: Sequence[str]
    out_dir: Path
    force: bool


@dataclass(frozen=True)
class KindResult:
    kind: str
    status: str  # "ok", "skipped" or "failed"
    detail: str


def check_single_tenant(series: Sequence[Series], spec: KindSpec, tenant: TenantConfig) -> None:
    """On a shared project, fail unless every series carries the tenant attribute with only the tenant's value."""
    if spec.tenant_scope != SHARED_ONLY or not tenant.shared_project or not spec.tenant_attribute:
        return
    prefix = f"{spec.tenant_attribute}="
    values = {
        str(label)[len(prefix):]
        for item in series
        for label in item.get("group-labels", [])  # type: ignore[attr-defined]
        if str(label).startswith(prefix)
    }
    if values != {getattr(tenant, spec.tenant_value)}:
        raise TenantSafetyError(f"{spec.kind}: {spec.tenant_attribute} values {sorted(values)} do not match tenant {tenant.code}")


def _skip_reason(spec: KindSpec, request: ExportRequest, path: Path) -> str | None:
    reason = spec.unavailable_reason(request.tenant)
    if reason:
        return reason
    if path.exists() and not request.force:
        return f"{path.name} already exists (use --force to overwrite)"
    return None


def _fetch(spec: KindSpec, request: ExportRequest, target: ExportTarget, deps: Dependencies) -> list[Series]:
    base_url, org = ENDPOINTS[target.region.upper()]
    oldest, youngest = utc_day_window(request.day)
    uql = expand_query(spec.query_kind, request.tenant)
    LOGGER.debug(
        "lightstep query start %s",
        redact_params({"kind": spec.kind, "project": target.project, "region": target.region,
                       "query_fingerprint": hashlib.sha256(uql.encode()).hexdigest()[:12], "uql": uql},
                      {"kind", "project", "region", "query_fingerprint"}),
    )
    series = fetch_all_series(
        deps.transport, project=Project(base_url, org, target.project), token=deps.tokens.token(target.region), uql=uql,
        oldest=oldest, youngest=youngest, output_period=spec.output_period_s,
    )
    if not series:
        raise LightstepError(f"{spec.kind}: no series returned for {request.day}; is it older than the ~7 day retention?")
    return series


def _build_and_write(spec: KindSpec, request: ExportRequest, series: Sequence[Series], path: Path) -> int:
    rows = spec.row_builder(series, expected_columns(spec.kind, request.tenant))
    request.out_dir.mkdir(parents=True, exist_ok=True)
    write_rows(path, rows, force=request.force)
    return len(rows) - 1


def export_kind(kind: str, request: ExportRequest, deps: Dependencies) -> KindResult:
    """Fetches and writes one kind; failures are logged once here and returned, not raised."""
    spec = get_kind(kind)
    path = request.out_dir / output_file_name(kind, request.day)
    reason = _skip_reason(spec, request, path)
    if reason:
        LOGGER.warning("skipping %s: %s", kind, reason)
        return KindResult(kind, "skipped", reason)
    started = time.monotonic()
    try:
        series = _fetch(spec, request, deps.resolve_target(kind, request.tenant), deps)
        check_single_tenant(series, spec, request.tenant)
        row_count = _build_and_write(spec, request, series, path)
    except (LightstepError, TenantSafetyError, FileExistsRefused, ValueError, KeyError, OSError) as exc:
        LOGGER.exception("export of %s failed", kind)
        return KindResult(kind, "failed", f"{type(exc).__name__}: {exc}")
    oldest, youngest = utc_day_window(request.day)
    LOGGER.info(
        "exported %s duration_ms=%d rows=%d series=%d base_slices=%d file=%s",
        kind, int((time.monotonic() - started) * 1000), row_count, len(series), len(split_window(oldest, youngest)), path.name,
    )
    return KindResult(kind, "ok", f"{row_count} rows -> {path}")


def input_check_applies(kinds: Sequence[str]) -> bool:
    """The Step 0 input check needs all core kinds in the run."""
    return set(CORE_KINDS) <= set(kinds)


def drm_expected(kinds: Sequence[str], results: Sequence[KindResult]) -> bool:
    """DRM files are required by the input check only when both DRM kinds ran and none was skipped."""
    return set(DRM_REQUIRED) <= set(kinds) and all(r.status != "skipped" for r in results if r.kind in DRM_REQUIRED)


def run_export(request: ExportRequest, deps: Dependencies) -> int:
    """Exports every kind (continuing past failures), runs the input check when applicable, and returns the exit code."""
    LOGGER.info("run start tenant=%s date=%s kinds=%s output_dir=%s", request.tenant.code, request.day, ",".join(request.kinds), request.out_dir)
    results = [export_kind(kind, request, deps) for kind in request.kinds]
    ok = not any(r.status == "failed" for r in results)
    report: str | None = None
    if input_check_applies(request.kinds):
        report, check_ok = deps.input_check(request.out_dir, drm_expected(request.kinds, results))
        ok = ok and check_ok
    else:
        LOGGER.info("input check skipped: it needs all of %s", ",".join(CORE_KINDS))
    deps.report(results, report)
    LOGGER.info("run end ok=%s summary=%s", ok, "; ".join(f"{r.kind}={r.status}" for r in results))
    return 0 if ok else 1


def print_report(results: Sequence[KindResult], check_report: str | None) -> None:
    for result in results:
        print(f"{result.status.upper():8} {result.kind}: {result.detail}")
    if check_report is not None:
        print(check_report)
