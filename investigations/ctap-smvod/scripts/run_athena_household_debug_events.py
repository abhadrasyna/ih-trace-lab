#!/usr/bin/env python3
"""
Live boto3/Athena runner that exports EVERY debug event (all eventclass/eventid, full `eventdata` JSON) for the
household/device pairs in an error-report CSV, over an inclusive date range, from the tenant's
`<id>_ccl_debug_events` table (query-catalog slug `ctap-smvod-household-debug-events`). Matches on
`clientid = '<deviceId>:<householdId>'`, so it also returns events outside any single session.

Usage:
    python3 run_athena_household_debug_events.py \
        --report-csv ../output/ZA/2026-10-01_2026-10-19_error_report_3xxx_rD_saW-t.csv --tenant ZA \
        --from 2026-10-01 --to 2026-10-21

    # Preview the query without touching Athena:
    ... --dry-run

Output: <report-csv minus .csv>_debug_events_all.csv (override with --out). Requires an AWS SSO profile with read
access to the tenant's unified_<id> database (auto-refreshed unless --skip-auth-check).
"""
import argparse
import csv
import logging
import os
import re
import sys
from datetime import datetime, timedelta

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.query_catalog import render_query
from lib.runtime import ensure_valid_credentials, run_athena_query, should_skip_athena
from lib.tenant_context import resolve_tenant_context
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_athena_household_debug_events")

QUERY_SLUG = "ctap-smvod-household-debug-events"
_TOKEN = re.compile(r"^[A-Za-z0-9_.-]+$")


def load_client_ids(report_path: str) -> list[str]:
    """Distinct '<deviceId>:<householdId>' clientids from the report CSV, sorted. Raises ValueError on bad input."""
    with open(report_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("householdId", "deviceId") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"column(s) {missing} missing in {report_path}")
        pairs = {(r["deviceId"].strip(), r["householdId"].strip()) for r in reader
                 if r["deviceId"].strip() and r["householdId"].strip()}
    if not pairs:
        raise ValueError(f"no householdId/deviceId pairs in {report_path}")
    bad = [p for p in pairs if not all(_TOKEN.match(x) for x in p)]
    if bad:
        raise ValueError(f"unsafe characters in id(s): {bad}")
    return sorted(f"{d}:{h}" for d, h in pairs)


def date_window(date_from: str, date_to: str) -> tuple[str, str]:
    """Inclusive YYYY-MM-DD range -> (start, end-exclusive) ISO timestamps. Raises ValueError if reversed/invalid."""
    start = datetime.strptime(date_from, "%Y-%m-%d")
    end = datetime.strptime(date_to, "%Y-%m-%d")
    if end < start:
        raise ValueError(f"--to {date_to} is before --from {date_from}")
    return start.strftime("%Y-%m-%dT00:00:00.000Z"), (end + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")


def build_query(ctx, database: str, client_ids: list[str], date_from: str, date_to: str) -> str:
    """Pure: render the catalog query for the clientids over the inclusive date range."""
    start, end = date_window(date_from, date_to)
    block = ",\n".join(f"    '{c}'" for c in client_ids)
    return render_query(QUERY_SLUG, {
        "database": database,
        "debug_events_table": ctx.debug_events_table,
        "datetime_start": start,
        "datetime_end": end,
        "client_ids_block": block,
    })


def main() -> None:
    init_logging("ctap-smvod-run_athena_household_debug_events")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report-csv", required=True, help="Error-report CSV with householdId and deviceId columns")
    ap.add_argument("--tenant", required=True, help="Tenant code from config/tenants.yaml (e.g. ZA)")
    ap.add_argument("--from", dest="date_from", required=True, help="Range start, YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", required=True, help="Range end, YYYY-MM-DD, inclusive")
    ap.add_argument("--out", default=None, help="Output CSV (default: <report-csv minus .csv>_debug_events_all.csv)")
    ap.add_argument("--profile", default=None, help="AWS SSO profile (default: from the tenant registry)")
    ap.add_argument("--database", default=None, help="Athena database (default: from the tenant registry)")
    ap.add_argument("--workgroup", default="primary", help="Athena workgroup (default: primary)")
    ap.add_argument("--output-location", default="s3://clarissaprod-apps-athena-query-results/",
                    help="S3 URI for Athena query results")
    ap.add_argument("--region", default=None, help="AWS region override (default: from the tenant registry)")
    ap.add_argument("--poll-interval", type=int, default=2, help="Seconds between status polls (default: 2)")
    ap.add_argument("--timeout", type=int, default=900, help="Max seconds to wait for the query (default: 900)")
    ap.add_argument("--dry-run", action="store_true", help="Print the filled-in query and exit, without touching Athena")
    ap.add_argument("--skip-auth-check", action="store_true", help="Skip the SSO credential check/auto-refresh pre-flight")
    ap.add_argument("--force", action="store_true", help="Re-run Athena even if the output CSV already has data")
    args = ap.parse_args()

    try:
        ctx = resolve_tenant_context(args.tenant)
        client_ids = load_client_ids(args.report_csv)
        database = args.database or ctx.database
        query = build_query(ctx, database, client_ids, args.date_from, args.date_to)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    profile = args.profile or ctx.profile
    region = args.region or ctx.region
    out_path = args.out or os.path.splitext(args.report_csv)[0] + "_debug_events_all.csv"

    if args.dry_run:
        sys.stdout.write(query)
        return
    if should_skip_athena(out_path, force=args.force):
        return
    if not args.skip_auth_check:
        try:
            ensure_valid_credentials(profile)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    print(f"Starting Athena query [{ctx.code}] on {database}.{ctx.debug_events_table} for {len(client_ids)} "
          f"clientid(s), {args.date_from}..{args.date_to} (profile={profile})...", file=sys.stderr)
    try:
        result = run_athena_query(sql=query, params={}, output_path=out_path, profile=profile, database=database,
                                  workgroup=args.workgroup, output_location=args.output_location, region=region,
                                  poll_interval=args.poll_interval, timeout=args.timeout)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {result.row_count} rows to {out_path}", file=sys.stderr)
    LOGGER.info("Completed run_athena_household_debug_events rows=%d out=%s", result.row_count, out_path)


if __name__ == "__main__":
    main()
