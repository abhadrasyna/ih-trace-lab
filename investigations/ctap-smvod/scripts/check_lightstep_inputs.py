"""Step 0: validate the hand-exported Lightstep CSVs for a date, for every tenant, before the pipeline runs.

Checks per tenant (see lib/lightstep_inputs.py): required files present (ctap, smvod, smvod-ts; plus
mdrmfe/mdrm-lrm with --drm), numbered parts contiguous and matching across artifacts, combined-file sidecar
in sync, schema and non-empty, rows belong to the tenant, and smvod-ts covers the UTC day without gaps or a
truncated last part. Exits 1 on any FAIL.

Usage:
    python3 check_lightstep_inputs.py --date 26102026
    python3 check_lightstep_inputs.py --date 26102026 --tenant ZM --tolerance-minutes 30
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.lightstep_inputs import Settings, format_legend, format_report, has_failures, validate_tenant
from lib.runtime import ddmmyyyy_to_iso
from lib.tenant_context import discover_tenants, lightstep_dir, require_lightstep_dir, resolve_tenant_context
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.check_lightstep_inputs")


def run_checks(
    tenants: list[str], date_iso: str, settings: Settings, drm_dir: Path | None = None
) -> tuple[str, bool]:
    """Returns (report text for every tenant, True when no tenant has a FAIL)."""
    blocks, ok = [], True
    for code in tenants:
        findings = validate_tenant(lightstep_dir(code), date_iso, resolve_tenant_context(code), settings, drm_dir)
        blocks.append(format_report(code, findings))
        ok = ok and not has_failures(findings)
    return "\n".join(blocks + [format_legend()]), ok


def select_tenants(requested: str | None, date_iso: str) -> list[str]:
    if requested:
        code = resolve_tenant_context(requested).code
        require_lightstep_dir(code)
        return [code]
    tenants = discover_tenants(date_iso)
    if not tenants:
        raise FileNotFoundError(f"No tenant has Lightstep input for {date_iso}")
    return tenants


def main() -> None:
    init_logging("ctap-smvod-check_lightstep_inputs")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 26102026")
    ap.add_argument("--tenant", default=None, help="Tenant code; default: every tenant with Lightstep input for --date")
    ap.add_argument("--drm", action="store_true", help="Also require the mdrmfe and mdrm-lrm exports")
    ap.add_argument("--drm-dir", default=None, help="Folder with the mDRM exports (default: the tenant's Lightstep folder); needs --tenant")
    ap.add_argument("--tolerance-minutes", type=int, default=15, help="Allowed distance of first/last span from 00:00/24:00 UTC")
    ap.add_argument("--max-gap-minutes", type=int, default=15, help="Longest allowed uncovered gap between consecutive parts")
    ap.add_argument("--row-cap", type=int, default=500, help="Rows at which a Lightstep span-samples export is truncated")
    args = ap.parse_args()
    if args.drm_dir and not args.tenant:
        ap.error("--drm-dir requires --tenant")
    try:
        date_iso = ddmmyyyy_to_iso(args.date)
        tenants = select_tenants(args.tenant, date_iso)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    settings = Settings(
        tolerance=timedelta(minutes=args.tolerance_minutes),
        max_gap=timedelta(minutes=args.max_gap_minutes),
        row_cap=args.row_cap,
        include_drm=args.drm,
    )
    report, ok = run_checks(tenants, date_iso, settings, Path(args.drm_dir) if args.drm_dir else None)
    print(report)
    LOGGER.info("Completed check_lightstep_inputs date=%s tenants=%s ok=%s", args.date, ",".join(tenants), ok)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
