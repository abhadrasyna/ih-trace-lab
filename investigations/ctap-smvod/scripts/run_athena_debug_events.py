#!/usr/bin/env python3
"""
Live boto3/Athena runner for BLUEPRINT.md Step 4 ("error detail + lifecycle"
enrichment against `e6auj7k7_ccl_debug_events`) using query-catalog slug
`ctap-smvod-debug-states`. Companion to
`run_athena_playback_outcome.py` (Step 3) -- same pattern (optional automated
alternative to the documented manual copy-paste-into-Athena-console workflow,
README.md §6/§7), but additionally folds in what used to be a separate manual
step: this script extracts the sessionId `IN (...)` filter itself (via
`extract_session_ids.extract_ids`) from the Step 2 merged report CSV, instead
of requiring `extract_session_ids.py` to be run by hand and its output pasted
into the query text.

Requires an AWS SSO profile with read access to unified_e6auj7k7 (see
scripts/lib/aws_sso.py / aws-access-cli/docs/aws-sso-setup.md); defaults to
`clarissa-insights-product`. Credentials are auto-refreshed via the `aws-sso`
CLI if stale/missing (skip with --skip-auth-check).

Usage:
    python3 run_athena_debug_events.py --date 2026-07-08

    # Explicit input CSV / sessionId column, if not the Step 2 default:
    python3 run_athena_debug_events.py --date 2026-07-08 \
        --input ../output/2026-07-08_setupsession.csv --column sessionId

    # Preview the filled-in query (including the resolved sessionId list)
    # without touching Athena:
    python3 run_athena_debug_events.py --date 2026-07-08 --dry-run

    # Override profile/database/workgroup/output dir if needed:
    python3 run_athena_debug_events.py --date 2026-07-08 \
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
from datetime import datetime, timedelta

import extract_session_ids

from lib.query_catalog import render_query
from lib.runtime import DEFAULT_PROFILE, ensure_valid_credentials, investigation_output_dir, run_athena_query, snapshot_output_path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "athena")
DEFAULT_OUTPUT_ROOT_DIR = str(investigation_output_dir())

# See BLUEPRINT.md Step 4 / queries/QUERY_CATALOG.md §11/§11a/§11b for why
# APP_KEEPALIVE must stay in this list (it's sometimes the only signal a
# session actually progressed) and why there's no eventclass = 'PLAYER'
# filter (dropped 13 Jul 2026, see the same catalog sections).
QUERY_SLUG = "ctap-smvod-debug-states"


def _default_output_path(date_iso: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{date_iso}_debug_states.csv")


def _validated_date_iso(raw_date: str) -> str:
    return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")


def _build_query(database, date, session_ids):
    start = f"{date}T00:00:00.000Z"
    next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end = f"{next_day}T00:00:00.000Z"
    session_ids_block = ",\n".join(f"    '{sid}'" for sid in session_ids)
    return render_query(
        QUERY_SLUG,
        {
            "database": database,
            "datetime_start": start,
            "datetime_end": end,
            "session_ids_block": session_ids_block,
        },
    )


def _default_input_path(date):
    ddmmyyyy = datetime.strptime(date, "%Y-%m-%d").strftime("%d%m%Y")
    return snapshot_output_path(ddmmyyyy, "setupsession", output_dir=DEFAULT_OUTPUT_ROOT_DIR)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Partition date, YYYY-MM-DD (e.g. 2026-07-08)")
    ap.add_argument(
        "--input", default=None,
        help="Step 2 merged report CSV to pull sessionIds from "
             "(default: ../output/YYYY-MM-DD_setupsession.csv, derived from --date)")
    ap.add_argument("--column", default="sessionId", help="sessionId column name (default: sessionId)")
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

    input_path = args.input or _default_input_path(date_iso)
    try:
        session_ids = extract_session_ids.extract_ids(input_path, args.column)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    if not session_ids:
        print(f"ERROR: no non-empty '{args.column}' values found in {input_path}", file=sys.stderr)
        sys.exit(1)
    print(f"Extracted {len(session_ids)} distinct sessionIds from {input_path}", file=sys.stderr)

    query = _build_query(args.database, date_iso, session_ids)

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

    print(
        f"Starting Athena query on {args.database}.e6auj7k7_ccl_debug_events for "
        f"{date_iso} ({len(session_ids)} sessionIds, profile={args.profile}, "
        f"workgroup={args.workgroup})...", file=sys.stderr)
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
