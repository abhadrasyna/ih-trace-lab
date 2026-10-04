#!/usr/bin/env python3
"""
Live boto3/Athena runner for BLUEPRINT.md Step 3 / query-catalog slug
`ctap-smvod-playback-outcome`
("playback outcome classification" enrichment). This is an *optional*
automated alternative to the documented manual copy-paste-into-Athena-console
workflow (README.md §6/§7) -- kept alongside it, same pattern as
scripts/lightstep_ctap_smvod_join.py being kept as a reference direct-API
attempt. The query catalog remains the source of truth for the SQL text
itself (`queries/athena/ctap-smvod-playback-outcome.sql`) -- this script
only automates *running* that exact query and downloading the result.

Requires an AWS SSO profile with read access to unified_e6auj7k7 (see
scripts/lib/aws_sso.py / aws-access-cli/docs/aws-sso-setup.md); defaults to
`clarissa-insights-product`. Credentials are auto-refreshed via the `aws-sso`
CLI if stale/missing (skip with --skip-auth-check).

Usage:
    python3 run_athena_playback_outcome.py --date 2026-07-08

    # Preview the query without running it against Athena:
    python3 run_athena_playback_outcome.py --date 2026-07-08 --dry-run

    # Override profile/database/workgroup/output dir if needed:
    python3 run_athena_playback_outcome.py --date 2026-07-08 \
        --profile clarissa-insights-product \
        --database unified_e6auj7k7 \
        --workgroup primary \
        --output-location s3://clarissaprod-apps-athena-query-results/ \
        --output-dir ../data/athena
"""
import argparse
import logging
import os
import sys
from datetime import datetime

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.query_catalog import render_query
from lib.runtime import DEFAULT_PROFILE, ensure_valid_credentials, run_athena_query
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_athena_playback_outcome")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "athena")

QUERY_SLUG = "ctap-smvod-playback-outcome"


def _default_output_path(date_iso: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{date_iso}_session.csv")


def _validated_date_iso(raw_date: str) -> str:
    return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")


def main():
    init_logging("ctap-smvod-run_athena_playback_outcome")
    LOGGER.info("Starting run_athena_playback_outcome")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Partition date, YYYY-MM-DD (e.g. 2026-07-08)")
    ap.add_argument("--profile", default=DEFAULT_PROFILE, help=f"AWS SSO profile (default: {DEFAULT_PROFILE})")
    ap.add_argument("--database", default="unified_e6auj7k7", help="Athena database (default: unified_e6auj7k7)")
    ap.add_argument("--workgroup", default="primary", help="Athena workgroup (default: primary)")
    ap.add_argument(
        "--output-location",
        default="s3://clarissaprod-apps-athena-query-results/",
        help="S3 URI for Athena query results (default: s3://clarissaprod-apps-athena-query-results/)",
    )
    ap.add_argument(
        "--region", default="eu-central-1",
        help="AWS region override (default: eu-central-1 -- the "
             "--output-location results bucket only exists there, which "
             "differs from this profile's own configured region, "
             "us-east-1)")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory to write the CSV to (default: <repo>/data/athena)")
    ap.add_argument("--poll-interval", type=int, default=2, help="Seconds between status polls (default: 2)")
    ap.add_argument("--timeout", type=int, default=300, help="Max seconds to wait for query completion (default: 300)")
    ap.add_argument("--dry-run", action="store_true", help="Print the filled-in query and exit, without touching Athena")
    ap.add_argument("--skip-auth-check", action="store_true", help="Skip the SSO credential check/auto-refresh pre-flight")
    args = ap.parse_args()

    try:
        date_iso = _validated_date_iso(args.date)
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got '{args.date}'", file=sys.stderr)
        sys.exit(1)

    query = render_query(QUERY_SLUG, {"database": args.database, "date": date_iso})

    if args.dry_run:
        sys.stdout.write(query)
        LOGGER.info("Completed run_athena_playback_outcome dry_run date=%s", date_iso)
        return

    if not args.skip_auth_check:
        try:
            already_valid = ensure_valid_credentials(args.profile)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        if not already_valid:
            print(f"Refreshed SSO credentials for profile '{args.profile}' via aws-sso.", file=sys.stderr)

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = _default_output_path(date_iso, args.output_dir)

    print(f"Starting Athena query on {args.database}.unified_sessions for {date_iso} "
          f"(profile={args.profile}, workgroup={args.workgroup})...", file=sys.stderr)
    try:
        result = run_athena_query(
            sql=query,
            params={},
            output_path=out_path,
            profile=args.profile,
            database=args.database,
            workgroup=args.workgroup,
            output_location=args.output_location,
            region=args.region,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Wrote {result.row_count} rows to {out_path}", file=sys.stderr)
    LOGGER.info(
        "Completed run_athena_playback_outcome rows=%d out=%s",
        result.row_count,
        out_path,
    )


if __name__ == "__main__":
    main()
