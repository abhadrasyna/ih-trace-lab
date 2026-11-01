"""Export one tenant's daily Lightstep CSVs (ctap, smvod, smvod-ts, mdrmfe and the four mDRM kinds) through the public API.

Writes ``<date>_<kind>.csv`` in the UI export format into ``data/lightstep/<TENANT>/`` (or ``--output-dir``),
then runs the Step 0 input check on that folder. Existing files are skipped unless ``--force`` is given.
Lightstep keeps about 7 days, so run within a week of the UTC day. Tokens come from ``LIGHTSTEP_API_KEY_EU`` /
``LIGHTSTEP_API_KEY_US`` in the environment or the gitignored root ``.env``.

Usage:
    python3 export_lightstep_day.py --tenant ZA
    python3 export_lightstep_day.py --tenant ZM --date 2026-10-29 --kinds ctap smvod --output-dir /tmp/ls --force
Exit code: 0 only when every kind was written (or skipped) and the input check passed.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.lightstep_inputs import Settings, format_legend, format_report, has_failures, validate_tenant
from lib.tenant_context import lightstep_dir, resolve_tenant_context

from scripts.lib.lightstep_api import (
    LightstepError,
    Project,
    Series,
    Transport,
    UrllibTransport,
    fetch_all_series,
    load_token,
    split_window,
    utc_day_window,
)
from scripts.lib.lightstep_csv import FileExistsRefused, build_rows, write_rows
from scripts.lib.lightstep_export_kinds import (
    KINDS,
    MDRM,
    SHARED_ONLY,
    ExportTarget,
    expand_query,
    expected_columns,
    get_kind,
    output_file_name,
    resolve_target,
)
from scripts.lib.lightstep_smvod_ts import derive_rows
from src.lib.logging.bootstrap import init_logging
from src.lib.logging.redact import redact_params
from src.tenant_registry import TenantConfig, TenantRegistry

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.export_lightstep_day")
ENDPOINTS = {
    "EU": ("https://api.eu.lightstep.com/public/v0.2", "Synamedia-EU"),
    "US": ("https://api.lightstep.com/public/v0.2", "Synamedia"),
}
DERIVED_PERIOD_S = 1
CORE_KINDS = ("ctap", "smvod", "smvod-ts")
DRM_REQUIRED = ("mdrmfe", "mdrm-lrm")
InputCheck = Callable[[Path, bool], tuple[str, bool]]


class TenantSafetyError(ValueError):
    """A shared-project export does not contain exactly the requested tenant."""


@dataclass(frozen=True)
class KindResult:
    kind: str
    status: str  # "ok", "skipped" or "failed"
    detail: str


def default_date(now: datetime | None = None) -> str:
    """Yesterday in UTC as ``YYYY-MM-DD``."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return (moment.date() - timedelta(days=1)).isoformat()


def check_single_tenant(series: Sequence[Series], kind: str, tenant: TenantConfig) -> None:
    """On a shared project, fail unless every series carries the tenant attribute with only the tenant's value."""
    spec = get_kind(kind)
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
        raise TenantSafetyError(f"{kind}: {spec.tenant_attribute} values {sorted(values)} do not match tenant {tenant.code}")


def _skip_reason(kind: str, tenant: TenantConfig) -> str | None:
    if get_kind(kind).system == MDRM and not (tenant.mdrm_tenant_id and tenant.mdrm_project):
        return f"tenant {tenant.code} has no registered mDRM tenant id"
    return None


def _fetch(kind: str, tenant: TenantConfig, target: ExportTarget, day: str, transport: Transport, token: str) -> list[Series]:
    spec = get_kind(kind)
    base_url, org = ENDPOINTS[target.region.upper()]
    oldest, youngest = utc_day_window(day)
    source = spec.derived_from or kind
    uql = expand_query(source, tenant)
    LOGGER.debug(
        "lightstep query start %s",
        redact_params({"kind": kind, "project": target.project, "region": target.region,
                       "query_fingerprint": hashlib.sha256(uql.encode()).hexdigest()[:12], "uql": uql}, {"kind", "project", "region", "query_fingerprint"}),
    )
    return fetch_all_series(
        transport, project=Project(base_url, org, target.project), token=token, uql=uql,
        oldest=oldest, youngest=youngest, output_period=DERIVED_PERIOD_S if spec.derived_from else None,
    )


def export_kind(
    kind: str, *, tenant: TenantConfig, day: str, out_dir: Path, force: bool, transport: Transport, tokens: dict[str, str]
) -> KindResult:
    """Fetches and writes one kind; returns its result. Failures are logged once here and returned, not raised."""
    reason = _skip_reason(kind, tenant)
    if reason:
        LOGGER.warning("skipping %s: %s", kind, reason)
        return KindResult(kind, "skipped", reason)
    path = out_dir / output_file_name(kind, day)
    if path.exists() and not force:
        LOGGER.info("skipping %s: %s already exists (use --force to overwrite)", kind, path.name)
        return KindResult(kind, "skipped", f"{path.name} already exists")
    started = time.monotonic()
    try:
        target = resolve_target(kind, tenant)
        region = target.region.upper()
        if region not in tokens:
            tokens[region] = load_token(region)
        series = _fetch(kind, tenant, target, day, transport, tokens[region])
        if not series:
            raise LightstepError(f"{kind}: no series returned for {day}; is it older than the ~7 day retention?")
        check_single_tenant(series, kind, tenant)
        columns = expected_columns(kind, tenant)
        rows = derive_rows(series, columns) if get_kind(kind).derived_from else build_rows(series, columns)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_rows(path, rows, force=force)
    except (LightstepError, TenantSafetyError, FileExistsRefused, ValueError, KeyError, OSError) as exc:
        LOGGER.exception("export of %s failed", kind)
        return KindResult(kind, "failed", f"{type(exc).__name__}: {exc}")
    oldest, youngest = utc_day_window(day)
    LOGGER.info(
        "exported %s duration_ms=%d rows=%d series=%d base_slices=%d file=%s",
        kind, int((time.monotonic() - started) * 1000), len(rows) - 1, len(series), len(split_window(oldest, youngest)), path.name,
    )
    return KindResult(kind, "ok", f"{len(rows) - 1} rows -> {path}")


def make_input_check(tenant_code: str, day: str) -> InputCheck:
    """Returns a check that validates a folder with the Step 0 validator for ``tenant_code`` and ``day``."""

    def check(directory: Path, include_drm: bool) -> tuple[str, bool]:
        findings = validate_tenant(directory, day, resolve_tenant_context(tenant_code), Settings(include_drm=include_drm))
        return "\n".join([format_report(tenant_code, findings), format_legend()]), not has_failures(findings)

    return check


def run_export(
    *, tenant: TenantConfig, day: str, kinds: Sequence[str], out_dir: Path, force: bool,
    transport: Transport, input_check: InputCheck,
) -> int:
    """Exports every kind (continuing past failures), runs the input check, and returns the exit code."""
    LOGGER.info("run start tenant=%s date=%s kinds=%s output_dir=%s", tenant.code, day, ",".join(kinds), out_dir)
    tokens: dict[str, str] = {}
    results = [export_kind(k, tenant=tenant, day=day, out_dir=out_dir, force=force, transport=transport, tokens=tokens) for k in kinds]
    for result in results:
        print(f"{result.status.upper():8} {result.kind}: {result.detail}")
    ok = not any(r.status == "failed" for r in results)
    if set(CORE_KINDS) <= set(kinds):
        drm = all(r.status != "skipped" for r in results if r.kind in DRM_REQUIRED) and set(DRM_REQUIRED) <= set(kinds)
        report, check_ok = input_check(out_dir, drm)
        print(report)
        ok = ok and check_ok
    else:
        LOGGER.info("input check skipped: it needs all of %s", ",".join(CORE_KINDS))
    LOGGER.info("run end ok=%s summary=%s", ok, "; ".join(f"{r.kind}={r.status}" for r in results))
    return 0 if ok else 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tenant", required=True, help="Tenant code from config/tenants.yaml, e.g. ZA")
    ap.add_argument("--date", default=None, help="UTC day as YYYY-MM-DD (default: yesterday UTC)")
    ap.add_argument("--kinds", nargs="+", default=list(KINDS), choices=list(KINDS), help="Kinds to export (default: all eight)")
    ap.add_argument("--output-dir", type=Path, default=None, help="Folder for the CSVs and the input check (default: data/lightstep/<TENANT>)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files instead of skipping them")
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None, transport: Transport | None = None, input_check: InputCheck | None = None) -> int:
    init_logging("export-lightstep-day")
    args = parse_args(argv)
    day = args.date or default_date()
    try:
        Date.fromisoformat(day)
        tenant = TenantRegistry().get(args.tenant)
    except (ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    out_dir = args.output_dir or lightstep_dir(tenant.code)
    return run_export(
        tenant=tenant, day=day, kinds=args.kinds, out_dir=out_dir, force=args.force,
        transport=transport or UrllibTransport(), input_check=input_check or make_input_check(tenant.code, day),
    )


if __name__ == "__main__":
    sys.exit(main())
