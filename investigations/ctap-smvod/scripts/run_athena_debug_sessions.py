#!/usr/bin/env python3
"""Exports the distinct abr-vod sessions (sessionId, first_event) in the debug-events table for one UTC day.

Query-catalog slug `ctap-smvod-debug-sessions`. Feeds `compare_lightstep_athena_sessions.py --debug`.
Writes `data/athena/<TENANT>/<date>_debug_sessions.csv`.

Usage:
    python3 run_athena_debug_sessions.py --date 2026-10-14 --tenant ZA [--table-suffix sept26] [--dry-run] [--force]
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.query_catalog import render_query
from lib.tenant_context import resolve_tenant_context
from lib.runtime import ensure_valid_credentials, investigation_data_dir, run_athena_query, should_skip_athena
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_athena_debug_sessions")
QUERY_SLUG = "ctap-smvod-debug-sessions"


def output_path(date_iso: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{date_iso}_debug_sessions.csv")


def day_bounds(date_iso: str) -> tuple[str, str]:
    """Pure: the UTC day as ISO datetime strings, [start, next-day start)."""
    day = datetime.strptime(date_iso, "%Y-%m-%d")
    return f"{date_iso}T00:00:00.000Z", f"{(day + timedelta(days=1)).strftime('%Y-%m-%d')}T00:00:00.000Z"


def main() -> None:
    init_logging("ctap-smvod-run_athena_debug_sessions")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", default="ZA", help="Tenant code from config/tenants.yaml (default: ZA)")
    ap.add_argument("--table-suffix", default=None, help="Month-suffixed debug table, e.g. sept26 (default: unsuffixed)")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--database", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--workgroup", default="primary")
    ap.add_argument("--output-location", default="s3://clarissaprod-apps-athena-query-results/")
    ap.add_argument("--output-dir", default=None, help="default: <investigation>/data/athena/<TENANT>")
    ap.add_argument("--poll-interval", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true", help="Print the query and exit")
    ap.add_argument("--skip-auth-check", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-run even if the output CSV already has data")
    args = ap.parse_args()

    try:
        ctx = resolve_tenant_context(args.tenant, table_suffix=args.table_suffix)
        start, end = day_bounds(args.date)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    profile = args.profile or ctx.profile
    database = args.database or ctx.database
    region = args.region or ctx.region
    out_dir = args.output_dir or str(investigation_data_dir("athena", tenant=args.tenant))
    out_path = output_path(args.date, out_dir)

    query = render_query(QUERY_SLUG, {
        "database": database, "debug_events_table": ctx.debug_events_table,
        "datetime_start": start, "datetime_end": end,
    })
    if args.dry_run:
        sys.stdout.write(query)
        return
    if should_skip_athena(out_path, force=args.force):
        return
    if not args.skip_auth_check:
        try:
            ensure_valid_credentials(profile)
        except Exception as exc:  # noqa: BLE001 - CLI boundary: report and exit non-zero
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    try:
        result = run_athena_query(
            sql=query, params={}, output_path=out_path, profile=profile, database=database,
            workgroup=args.workgroup, output_location=args.output_location, region=region,
            poll_interval=args.poll_interval, timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary: report and exit non-zero
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    LOGGER.info("Wrote %d rows to %s", result.row_count, out_path)


if __name__ == "__main__":
    main()
