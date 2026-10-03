#!/usr/bin/env python3
"""
Live boto3/Athena runner for BLUEPRINT.md Step 3 / queries/athena_session_outcome.md
("playback outcome classification" enrichment). This is an *optional*
automated alternative to the documented manual copy-paste-into-Athena-console
workflow (README.md §6/§7) -- kept alongside it, same pattern as
scripts/lightstep_ctap_smvod_join.py being kept as a reference direct-API
attempt. The manual workflow remains the source of truth for the query text
itself (queries/athena_session_outcome.md) -- this script only automates
*running* that exact query and downloading the result.

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

from lib.runtime import DEFAULT_PROFILE, ensure_valid_credentials, run_athena_query

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "athena")

QUERY_TEMPLATE = """SELECT
  parent_session_id AS sessionId,
  MAX(user_id)   AS householdId,
  MAX(device_id) AS deviceId,
  MAX(content)   AS content,
  COALESCE(
    MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
    CASE WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1
         THEN 'EBVS'
         ELSE 'INCOMPLETE_NO_DESTROY'
    END
  ) AS playback_outcome,
  MAX(CASE WHEN event_type = 'PLAY' THEN event_start END) AS event_start,
  MAX(CASE WHEN event_type = 'PLAY' THEN event_end END)   AS event_end,
  MAX(CASE WHEN event_type = 'REQUEST_VIEWING'
           THEN date_diff('millisecond', event_start, event_end) END) AS startup_time_ms,
  SUM(CASE WHEN event_type = 'BUFFERING' THEN 1 ELSE 0 END) AS buffering_count,
  SUM(CASE WHEN event_type = 'BUFFERING'
           THEN date_diff('millisecond', event_start, event_end) ELSE 0 END) AS buffering_total_ms
FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = '{date}'
GROUP BY parent_session_id;
"""


def _default_output_path(date_iso: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{date_iso}_session.csv")


def _validated_date_iso(raw_date: str) -> str:
    return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

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

    query = QUERY_TEMPLATE.format(date=date_iso)

    if args.dry_run:
        sys.stdout.write(query)
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


if __name__ == "__main__":
    main()
