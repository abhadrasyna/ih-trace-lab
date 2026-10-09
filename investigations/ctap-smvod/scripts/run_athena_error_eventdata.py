#!/usr/bin/env python3
"""
Live boto3/Athena runner that exports one day's raw `PLAYER_ERROR` events (full `eventdata` JSON plus
`messageid`/`clientid`) from the tenant's `<id>_ccl_debug_events` table, using query-catalog slug
`ctap-smvod-error-eventdata`. Its output is the input of `flatten_error_eventdata.py`
(`run_athena_debug_events.py`'s `debug_states.csv` only has extracted columns, not the raw eventdata).

The query covers all of the tenant's traffic for the day, not just Lightstep-matched sessions, so counts can
exceed the pipeline error report; the flattener de-duplicates on `messageid`.

Usage:
    python3 run_athena_error_eventdata.py --date 2026-10-04 --tenant ZM

    # Only some error codes (matched on eventdata.errorcode):
    python3 run_athena_error_eventdata.py --date 2026-10-04 --tenant ZM --codes 3016,6007

    # Preview the query without touching Athena:
    python3 run_athena_error_eventdata.py --date 2026-10-04 --tenant ZM --dry-run

Output: data/athena/<TENANT>/<date>_error_eventdata.csv. Requires an AWS SSO profile with read access to the
tenant's unified_<id> database (auto-refreshed unless --skip-auth-check).
"""
import argparse
import logging
import os
import re
import sys
from datetime import datetime, timedelta

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.query_catalog import render_query
from lib.runtime import ensure_valid_credentials, investigation_data_dir, run_athena_query, should_skip_athena
from lib.tenant_context import resolve_tenant_context
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_athena_error_eventdata")

QUERY_SLUG = "ctap-smvod-error-eventdata"
_CODE = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_codes(raw: str | None) -> list[str]:
    """Pure: '3016, 6007' -> ['3016', '6007']. Raises ValueError on any code that is not a plain token."""
    codes = [c.strip() for c in (raw or "").split(",") if c.strip()]
    bad = [c for c in codes if not _CODE.match(c)]
    if bad:
        raise ValueError(f"invalid error code(s): {bad}")
    return codes


def build_query(ctx, database: str, date_iso: str, codes: list[str]) -> str:
    """Pure: render the catalog query for one UTC day, optionally restricted to `codes`."""
    next_day = (datetime.strptime(date_iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    code_list = ", ".join(f"'{c}'" for c in codes)
    code_filter = f"AND json_extract_scalar(eventdata, '$.errorcode') IN ({code_list})" if codes else ""
    return render_query(QUERY_SLUG, {
        "database": database,
        "debug_events_table": ctx.debug_events_table,
        "datetime_start": f"{date_iso}T00:00:00.000Z",
        "datetime_end": f"{next_day}T00:00:00.000Z",
        "error_code_filter": code_filter,
    })


def output_path(date_iso: str, output_dir: str, codes: list[str] | None = None) -> str:
    """Unfiltered runs keep the default name; filtered runs embed the codes so caches never collide."""
    suffix = f"_codes-{'-'.join(sorted(codes))}" if codes else ""
    return os.path.join(output_dir, f"{date_iso}_error_eventdata{suffix}.csv")


def main() -> None:
    init_logging("ctap-smvod-run_athena_error_eventdata")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="Partition date, YYYY-MM-DD (e.g. 2026-10-04)")
    ap.add_argument("--codes", default=None, help="Comma-separated error codes to keep (default: every PLAYER_ERROR)")
    ap.add_argument("--tenant", required=True, help="Tenant code from config/tenants.yaml (e.g. ZM)")
    ap.add_argument("--profile", default=None, help="AWS SSO profile (default: from the tenant registry)")
    ap.add_argument("--database", default=None, help="Athena database (default: from the tenant registry)")
    ap.add_argument("--workgroup", default="primary", help="Athena workgroup (default: primary)")
    ap.add_argument("--output-location", default="s3://clarissaprod-apps-athena-query-results/",
                    help="S3 URI for Athena query results")
    ap.add_argument("--region", default=None, help="AWS region override (default: from the tenant registry)")
    ap.add_argument("--output-dir", default=None, help="Directory for the CSV (default: <repo>/data/athena/<TENANT>)")
    ap.add_argument("--poll-interval", type=int, default=2, help="Seconds between status polls (default: 2)")
    ap.add_argument("--timeout", type=int, default=300, help="Max seconds to wait for the query (default: 300)")
    ap.add_argument("--dry-run", action="store_true", help="Print the filled-in query and exit, without touching Athena")
    ap.add_argument("--skip-auth-check", action="store_true", help="Skip the SSO credential check/auto-refresh pre-flight")
    ap.add_argument("--force", action="store_true", help="Re-run Athena even if the output CSV already has data")
    args = ap.parse_args()

    try:
        ctx = resolve_tenant_context(args.tenant)
        date_iso = datetime.strptime(args.date, "%Y-%m-%d").strftime("%Y-%m-%d")
        codes = parse_codes(args.codes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    profile = args.profile or ctx.profile
    database = args.database or ctx.database
    region = args.region or ctx.region
    out_dir = args.output_dir or str(investigation_data_dir("athena", tenant=args.tenant))
    out_path = output_path(date_iso, out_dir, codes)
    query = build_query(ctx, database, date_iso, codes)

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

    os.makedirs(out_dir, exist_ok=True)
    print(f"Starting Athena query [{ctx.code}] on {database}.{ctx.debug_events_table} for {date_iso} "
          f"(codes={codes or 'all'}, profile={profile})...", file=sys.stderr)
    try:
        result = run_athena_query(sql=query, params={}, output_path=out_path, profile=profile, database=database,
                                  workgroup=args.workgroup, output_location=args.output_location, region=region,
                                  poll_interval=args.poll_interval, timeout=args.timeout)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {result.row_count} rows to {out_path}", file=sys.stderr)
    LOGGER.info("Completed run_athena_error_eventdata rows=%d out=%s", result.row_count, out_path)


if __name__ == "__main__":
    main()
