#!/usr/bin/env python3
"""
Live boto3/Athena runner for BLUEPRINT.md Step 4 ("error detail + lifecycle"
enrichment against the tenant's `<id>_ccl_debug_events` table) using query-catalog slug
`ctap-smvod-debug-states`. Companion to
`run_athena_playback_outcome.py` (Step 3) -- same pattern (optional automated
alternative to the documented manual copy-paste-into-Athena-console workflow,
README.md §6/§7), but additionally folds in what used to be a separate manual
step: this script extracts the sessionId `IN (...)` filter itself (via
`extract_session_ids.extract_ids`) from the Step 2 merged report CSV, instead
of requiring `extract_session_ids.py` to be run by hand and its output pasted
into the query text.

Requires an AWS SSO profile with read access to the tenant's unified_<id> database (see
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
        --tenant ZM \
        --workgroup primary \
        --output-location s3://clarissaprod-apps-athena-query-results/ \
        --output-dir ../data/athena
"""
import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timedelta

import extract_session_ids

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.query_catalog import render_query
from lib.tenant_context import resolve_tenant_context
from lib.runtime import ensure_valid_credentials, investigation_data_dir, run_athena_query, should_skip_athena, snapshot_output_path
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_athena_debug_events")

LEGACY_TENANT = "ZA"

# See BLUEPRINT.md Step 4 / queries/QUERY_CATALOG.md §11/§11a/§11b for why
# APP_KEEPALIVE must stay in this list (it's sometimes the only signal a
# session actually progressed) and why there's no eventclass = 'PLAYER'
# filter (dropped 13 Jul 2026, see the same catalog sections).
QUERY_SLUG = "ctap-smvod-debug-states"


# ~2000 ids is ~105 KB of SQL, well under Athena's 262144-byte query-string cap.
MAX_IDS_PER_QUERY = 2000


def _chunk_ids(session_ids, size=MAX_IDS_PER_QUERY):
    ids = list(session_ids)
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def _merge_csv_parts(part_paths, out_path):
    """Concatenates part CSVs (header from the first non-empty one) into out_path; returns data row count."""
    rows = 0
    header_written = False
    with open(out_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        for part in part_paths:
            with open(part, newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                header = next(reader, None)
                if header is None:
                    continue
                if not header_written:
                    writer.writerow(header)
                    header_written = True
                for row in reader:
                    writer.writerow(row)
                    rows += 1
    return rows


def _default_output_path(date_iso: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{date_iso}_debug_states.csv")


def _validated_date_iso(raw_date: str) -> str:
    return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")


def _build_query(ctx, database, date, session_ids):
    start = f"{date}T00:00:00.000Z"
    next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end = f"{next_day}T00:00:00.000Z"
    session_ids_block = ",\n".join(f"    '{sid}'" for sid in session_ids)
    return render_query(
        QUERY_SLUG,
        {
            "database": database,
            "debug_events_table": ctx.debug_events_table,
            "datetime_start": start,
            "datetime_end": end,
            "session_ids_block": session_ids_block,
        },
    )


def _default_input_path(date, tenant=None):
    ddmmyyyy = datetime.strptime(date, "%Y-%m-%d").strftime("%d%m%Y")
    return snapshot_output_path(ddmmyyyy, "setupsession", tenant=tenant)


def main():
    init_logging("ctap-smvod-run_athena_debug_events")
    LOGGER.info("Starting run_athena_debug_events")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Partition date, YYYY-MM-DD (e.g. 2026-07-08)")
    ap.add_argument(
        "--input", default=None,
        help="Step 2 merged report CSV to pull sessionIds from "
             "(default: ../output/YYYY-MM-DD_setupsession.csv, derived from --date)")
    ap.add_argument("--column", default="sessionId", help="sessionId column name (default: sessionId)")
    ap.add_argument("--tenant", default=None, help="Tenant code from config/tenants.yaml (default: ZA with the legacy flat data/ and output/ folders)")
    ap.add_argument("--profile", default=None, help="AWS SSO profile (default: from the tenant registry)")
    ap.add_argument("--database", default=None, help="Athena database (default: from the tenant registry)")
    ap.add_argument("--workgroup", default="primary", help="Athena workgroup (default: primary)")
    ap.add_argument(
        "--output-location",
        default="s3://clarissaprod-apps-athena-query-results/",
        help="S3 URI for Athena query results (default: s3://clarissaprod-apps-athena-query-results/)",
    )
    ap.add_argument(
        "--region", default=None,
        help="AWS region override (default: from the tenant registry, eu-central-1 -- the "
             "--output-location results bucket only exists there, which "
             "differs from this profile's own configured region, "
             "us-east-1)")
    ap.add_argument("--output-dir", default=None, help="Directory to write the CSV to (default: <repo>/data/athena[/<TENANT>])")
    ap.add_argument("--poll-interval", type=int, default=2, help="Seconds between status polls (default: 2)")
    ap.add_argument("--timeout", type=int, default=300, help="Max seconds to wait for query completion (default: 300)")
    ap.add_argument("--dry-run", action="store_true", help="Print the filled-in query and exit, without touching Athena")
    ap.add_argument("--skip-auth-check", action="store_true", help="Skip the SSO credential check/auto-refresh pre-flight")
    ap.add_argument("--force", action="store_true", help="Re-run Athena even if the output CSV already has data")
    args = ap.parse_args()

    try:
        ctx = resolve_tenant_context(args.tenant or LEGACY_TENANT)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    args.profile = args.profile or ctx.profile
    args.database = args.database or ctx.database
    args.region = args.region or ctx.region
    args.output_dir = args.output_dir or str(investigation_data_dir("athena", tenant=args.tenant))

    try:
        date_iso = _validated_date_iso(args.date)
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got '{args.date}'", file=sys.stderr)
        sys.exit(1)

    input_path = args.input or _default_input_path(date_iso, args.tenant)
    try:
        session_ids = extract_session_ids.extract_ids(input_path, args.column)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    if not session_ids:
        print(f"ERROR: no non-empty '{args.column}' values found in {input_path}", file=sys.stderr)
        sys.exit(1)
    print(f"Extracted {len(session_ids)} distinct sessionIds from {input_path}", file=sys.stderr)

    chunks = _chunk_ids(session_ids)
    queries = [_build_query(ctx, args.database, date_iso, chunk) for chunk in chunks]

    if args.dry_run:
        sys.stdout.write("\n".join(queries))
        LOGGER.info("Completed run_athena_debug_events dry_run date=%s", date_iso)
        return

    if should_skip_athena(_default_output_path(date_iso, args.output_dir), force=args.force):
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
        f"Starting Athena query [{ctx.code}] on {args.database}.{ctx.debug_events_table} for "
        f"{date_iso} ({len(session_ids)} sessionIds, profile={args.profile}, "
        f"workgroup={args.workgroup})...", file=sys.stderr)
    part_paths = []
    try:
        for i, query in enumerate(queries, start=1):
            part_path = out_path if len(queries) == 1 else f"{out_path}.part{i}"
            if len(queries) > 1:
                print(f"Chunk {i}/{len(queries)} ({len(chunks[i - 1])} sessionIds)...", file=sys.stderr)
            part_paths.append(part_path)
            result = run_athena_query(
                sql=query,
                params={},
                output_path=part_path,
                profile=args.profile,
                database=args.database,
                workgroup=args.workgroup,
                output_location=args.output_location,
                region=args.region,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
        if len(queries) > 1:
            row_count = _merge_csv_parts(part_paths, out_path)
        else:
            row_count = result.row_count
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if len(queries) > 1:
            for part in part_paths:
                if os.path.exists(part):
                    os.remove(part)

    print(f"Wrote {row_count} rows to {out_path}", file=sys.stderr)
    LOGGER.info(
        "Completed run_athena_debug_events rows=%d out=%s",
        row_count,
        out_path,
    )


if __name__ == "__main__":
    main()
