"""Per-kind export pipeline and run loop for the daily Lightstep export.

Everything external (transport, tokens, target resolution, the input check, result printing) is injected;
the only composition root is the CLI's ``main()``.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import partial
from datetime import datetime, timedelta, timezone
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
from scripts.lib.lightstep_parallel import JobRunner, ThreadJobRunner
from scripts.lib.lightstep_stitch import stitch_series
from scripts.lib.lightstep_export_checks import check_output, check_parts_complete
from scripts.lib.lightstep_parts import PartStore, Window, query_fingerprint
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
DEFAULT_PARTS_ROOT = Path(__file__).resolve().parents[2] / "tmp" / "lightstep-export"
INGEST_LAG = timedelta(hours=1)  # windows ending later than now minus this may still be filling, so they are never cached
DRM_REQUIRED = ("mdrmfe", "mdrm-lrm")
InputCheck = Callable[[Path, bool], tuple[str, bool]]
TargetResolver = Callable[[str, TenantConfig], ExportTarget]


class TenantSafetyError(ValueError):
    """A shared-project export does not contain exactly the requested tenant."""


class SanityCheckError(ValueError):
    """A written export does not match its parts (header, BOM or row count)."""


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
    job_runner: JobRunner = field(default_factory=ThreadJobRunner)


@dataclass(frozen=True)
class ExportRequest:
    tenant: TenantConfig
    day: str
    kinds: Sequence[str]
    out_dir: Path
    force: bool
    part_hours: int = 1
    fresh: bool = False
    parts_root: Path = field(default_factory=lambda: DEFAULT_PARTS_ROOT)

    def __post_init__(self) -> None:
        if not 1 <= self.part_hours <= 24:
            raise ValueError("part_hours must be between 1 and 24")

    @property
    def parts_dir(self) -> Path:
        return self.parts_root / f"{self.tenant.code}_{self.day}"


@dataclass(frozen=True)
class KindResult:
    kind: str
    status: str  # "ok", "skipped" or "failed"
    detail: str
    problems: tuple[str, ...] = ()  # sanity-check findings (a)-(c); any finding keeps the parts folder
    verified: bool = False  # a skipped kind with nothing pending (not applicable, or output matches its parts); does not block cleanup


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


def _plan(spec: KindSpec, request: ExportRequest, target: ExportTarget) -> tuple[str, list[Window], list[str]]:
    """The query text, the part windows and each window's fingerprint."""
    oldest, youngest = utc_day_window(request.day)
    uql = expand_query(spec.query_kind, request.tenant)
    windows = split_window(oldest, youngest, timedelta(hours=request.part_hours))
    prints = [
        query_fingerprint(uql=uql, project=target.project, region=target.region, period=spec.output_period_s,
                          kind=spec.kind, window=[w[0].isoformat(), w[1].isoformat()])
        for w in windows
    ]
    return uql, windows, prints


def _fetch(spec: KindSpec, request: ExportRequest, target: ExportTarget, deps: Dependencies) -> list[Series]:
    base_url, org = ENDPOINTS[target.region.upper()]
    uql, windows, prints = _plan(spec, request, target)
    project = Project(base_url, org, target.project)
    LOGGER.debug(
        "lightstep query start %s",
        redact_params({"kind": spec.kind, "project": target.project, "region": target.region,
                       "query_fingerprint": hashlib.sha256(uql.encode()).hexdigest()[:12], "uql": uql},
                      {"kind", "project", "region", "query_fingerprint"}),
    )
    store = PartStore(request.parts_dir)
    parts = [store.load(spec.kind, i, w, prints[i - 1]) for i, w in enumerate(windows, start=1)]
    missing = [i for i, part in enumerate(parts) if part is None]
    LOGGER.info("kind=%s parts total=%d reused=%d remaining=%d", spec.kind, len(windows), len(windows) - len(missing), len(missing))
    def fetch_part(i: int) -> tuple[list[Series], int]:
        started = time.monotonic()
        fetched = fetch_all_series(
            deps.transport, project=project, token=deps.tokens.token(target.region), uql=uql,
            oldest=windows[i][0], youngest=windows[i][1], output_period=spec.output_period_s,
        )
        if windows[i][1] <= datetime.now(timezone.utc) - INGEST_LAG:
            store.save(spec.kind, i + 1, windows[i], prints[i], fetched)
        else:
            LOGGER.info("part %d/%d kind=%s ends within the ingestion lag; not cached", i + 1, len(windows), spec.kind)
        return fetched, int((time.monotonic() - started) * 1000)

    kind_started = time.monotonic()
    finished = 0

    def collect(position: int, result: tuple[list[Series], int]) -> None:
        nonlocal finished
        finished += 1
        i, (fetched, duration_ms) = missing[position], result
        parts[i] = fetched
        eta_s = int((time.monotonic() - kind_started) / finished * (len(missing) - finished))
        LOGGER.info("part %d/%d kind=%s window=%s..%s series=%d duration_ms=%d eta_s=%d", i + 1, len(windows), spec.kind,
                    windows[i][0].isoformat(), windows[i][1].isoformat(), len(fetched), duration_ms, eta_s)

    deps.job_runner.run([partial(fetch_part, i) for i in missing], collect)
    series = stitch_series([part or [] for part in parts])
    LOGGER.info("stitching kind=%s parts=%d series=%d", spec.kind, len(windows), len(series))
    if not series:
        raise LightstepError(f"{spec.kind}: no series returned for {request.day}; is it older than the ~7 day retention?")
    return series


def _build_and_write(spec: KindSpec, request: ExportRequest, series: Sequence[Series], path: Path) -> int:
    rows = spec.row_builder(series, expected_columns(spec.kind, request.tenant))
    request.out_dir.mkdir(parents=True, exist_ok=True)
    write_rows(path, rows, force=request.force)
    return len(rows) - 1


def _verify_kind(spec: KindSpec, request: ExportRequest, target: ExportTarget, path: Path) -> tuple[str, ...]:
    """Checks (a)-(c) for one kind, re-reading its parts and output file from disk."""
    _, windows, prints = _plan(spec, request, target)
    store = PartStore(request.parts_dir)
    loaded = [store.load(spec.kind, i, w, prints[i - 1]) for i, w in enumerate(windows, start=1)]
    gaps = check_parts_complete(loaded)  # windows inside the ingestion lag are never cached, so today's export keeps its parts
    for gap in gaps:
        LOGGER.warning("sanity check %s: %s", spec.kind, gap)
    if gaps:
        return tuple(f"{spec.kind}: {gap}" for gap in gaps)
    broken = check_output(path, expected_columns(spec.kind, request.tenant), [p or [] for p in loaded],
                          derived=spec.derived_from is not None)
    if broken:
        raise SanityCheckError("; ".join(broken))
    return ()


def _existing_output_verified(spec: KindSpec, request: ExportRequest, deps: Dependencies, path: Path) -> bool:
    """True when nothing is pending: the kind does not apply to the tenant, or its existing output matches the verified parts."""
    if spec.unavailable_reason(request.tenant):
        return True
    if not path.exists():
        return False
    try:
        return not _verify_kind(spec, request, deps.resolve_target(spec.kind, request.tenant), path)
    except (SanityCheckError, ValueError, KeyError, OSError):
        return False


def export_kind(kind: str, request: ExportRequest, deps: Dependencies) -> KindResult:
    """Fetches and writes one kind; failures are logged once here and returned, not raised."""
    spec = get_kind(kind)
    path = request.out_dir / output_file_name(kind, request.day)
    reason = _skip_reason(spec, request, path)
    if reason:
        LOGGER.warning("skipping %s: %s", kind, reason)
        return KindResult(kind, "skipped", reason, verified=_existing_output_verified(spec, request, deps, path))
    started = time.monotonic()
    try:
        target = deps.resolve_target(kind, request.tenant)
        series = _fetch(spec, request, target, deps)
        check_single_tenant(series, spec, request.tenant)
        row_count = _build_and_write(spec, request, series, path)
        try:
            problems = _verify_kind(spec, request, target, path)
        except SanityCheckError:
            path.unlink(missing_ok=True)  # a rerun would otherwise skip the bad file as "already exists"
            raise
    except (LightstepError, TenantSafetyError, SanityCheckError, FileExistsRefused, ValueError, KeyError, OSError) as exc:
        LOGGER.exception("export of %s failed", kind)
        return KindResult(kind, "failed", f"{type(exc).__name__}: {exc}")
    oldest, youngest = utc_day_window(request.day)
    LOGGER.info(
        "exported %s duration_ms=%d rows=%d series=%d base_slices=%d file=%s",
        kind, int((time.monotonic() - started) * 1000), row_count, len(series), len(split_window(oldest, youngest)), path.name,
    )
    LOGGER.info("kind done kind=%s elapsed=%ds", kind, int(time.monotonic() - started))
    return KindResult(kind, "ok", f"{row_count} rows -> {path}", problems)


def input_check_applies(kinds: Sequence[str]) -> bool:
    """The Step 0 input check needs all core kinds in the run."""
    return set(CORE_KINDS) <= set(kinds)


def drm_expected(kinds: Sequence[str], results: Sequence[KindResult]) -> bool:
    """DRM files are required by the input check only when both DRM kinds ran and none was skipped."""
    return set(DRM_REQUIRED) <= set(kinds) and all(r.status != "skipped" for r in results if r.kind in DRM_REQUIRED)


def cleanup_parts(request: ExportRequest, results: Sequence[KindResult], *, check_ok: bool) -> bool:
    """Deletes this run's ``<TENANT>_<date>/`` parts folder only when every kind is ok with no findings and (d) passed."""
    blockers = [r.problems for r in results if r.problems] + [f"{r.kind} {r.status}" for r in results if r.status != "ok" and not (r.status == "skipped" and r.verified)]
    if blockers or not check_ok:
        LOGGER.warning("parts kept for resume at %s: %s", request.parts_dir, blockers or "input check failed or run had failures")
        return False
    if not request.parts_dir.exists():
        return False
    foreign = sorted({p.name.rsplit("_", 1)[0] for p in request.parts_dir.glob("*.json")} - set(request.kinds))
    if foreign:
        LOGGER.warning("parts kept: %s holds resume parts of kinds not in this run: %s", request.parts_dir, foreign)
        return False
    try:
        PartStore(request.parts_dir).discard()
    except OSError:
        LOGGER.exception("could not delete parts folder %s", request.parts_dir)
        return False
    LOGGER.info("cleanup tmp=%s deleted after passing sanity checks", request.parts_dir)
    return True


def run_export(request: ExportRequest, deps: Dependencies) -> int:
    """Exports every kind (continuing past failures), runs the input check when applicable, and returns the exit code."""
    LOGGER.info("run start tenant=%s date=%s kinds=%s output_dir=%s", request.tenant.code, request.day, ",".join(request.kinds), request.out_dir)
    if request.fresh:
        PartStore(request.parts_dir).discard()
        LOGGER.info("fresh run: discarded parts folder %s", request.parts_dir)
    results = [export_kind(kind, request, deps) for kind in request.kinds]
    ok = not any(r.status == "failed" for r in results)
    report: str | None = None
    if input_check_applies(request.kinds):
        report, check_ok = deps.input_check(request.out_dir, drm_expected(request.kinds, results))
        ok = ok and check_ok
    else:
        LOGGER.info("input check skipped: it needs all of %s", ",".join(CORE_KINDS))
    cleanup_parts(request, results, check_ok=ok)
    deps.report(results, report)
    LOGGER.info("run end ok=%s summary=%s", ok, "; ".join(f"{r.kind}={r.status}" for r in results))
    return 0 if ok else 1


def print_report(results: Sequence[KindResult], check_report: str | None) -> None:
    for result in results:
        print(f"{result.status.upper():8} {result.kind}: {result.detail}")
    if check_report is not None:
        print(check_report)
