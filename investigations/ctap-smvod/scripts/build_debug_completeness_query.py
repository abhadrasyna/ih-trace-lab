#!/usr/bin/env python3
"""
Fill the §15/§16 "PLAYING but no PLAY row" follow-up query (query-catalog
slug `ctap-smvod-debug-completeness`) with the parent_session_id values from a CSV
export (e.g. queries/exploration/playing_sessionid.csv, the output of the
§15 unified_sessions query) and produce a ready-to-paste Athena query that
checks e6auj7k7_ccl_debug_events for a complete CREATE->PLAYING->DESTROY
lifecycle for each of those sessions.

Usage:
    python3 build_debug_completeness_query.py \
        --input ../queries/exploration/playing_sessionid.csv \
        --start 2025-10-09T00:00:00.000Z \
        --end   2025-10-10T00:00:00.000Z

    # Write straight to a .sql file instead of stdout:
    python3 build_debug_completeness_query.py \
        --input ../queries/exploration/playing_sessionid.csv \
        --start 2025-10-09T00:00:00.000Z \
        --end   2025-10-10T00:00:00.000Z \
        --out   ../queries/exploration/playing_no_play_debug_check.sql
"""
import argparse
import logging
from lib import csv_io_compat as csv
import sys
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.build_debug_completeness_query")

from lib.query_catalog import render_query

QUERY_SLUG = "ctap-smvod-debug-completeness"


def main():
    init_logging("ctap-smvod-build_debug_completeness_query")
    LOGGER.info("Starting build_debug_completeness_query")
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with a parent_session_id/sessionId column (e.g. §15 export)")
    ap.add_argument("--column", default="parent_session_id", help="Column name to extract (default: parent_session_id)")
    ap.add_argument("--start", required=True, help="Datetime lower bound, e.g. 2025-10-09T00:00:00.000Z")
    ap.add_argument("--end", required=True, help="Datetime upper bound (exclusive), e.g. 2025-10-10T00:00:00.000Z")
    ap.add_argument("--out", default=None, help="Write the filled query here instead of stdout")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if args.column not in (reader.fieldnames or []):
            print(f"ERROR: column '{args.column}' not found in {args.input}. "
                  f"Available columns: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)
        ids = sorted({row[args.column] for row in reader if row.get(args.column)})

    if not ids:
        print(f"WARNING: no non-empty '{args.column}' values found in {args.input}", file=sys.stderr)
        sys.exit(1)

    session_ids_block = ",\n".join(f"          '{i}'" for i in ids)
    query = render_query(
        QUERY_SLUG,
        {
            "database": "unified_e6auj7k7",
            "datetime_start": args.start,
            "datetime_end": args.end,
            "eventclass": "PLAYER",
            "session_ids_block": session_ids_block,
        },
    )

    if args.out:
        with open(args.out, "w") as f:
            f.write(f"-- Generated from {args.input} ({len(ids)} distinct {args.column} values)\n")
            f.write(f"-- Checks e6auj7k7_ccl_debug_events for a complete CREATE->PLAYING->DESTROY\n")
            f.write(f"-- lifecycle for sessions flagged by the §15 query (PLAYING endreason, no PLAY row)\n\n")
            f.write(query)
        print(f"Wrote query for {len(ids)} session IDs to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(query)
        print(f"\n({len(ids)} distinct {args.column} values)", file=sys.stderr)

    LOGGER.info(
        "Completed build_debug_completeness_query session_ids=%d destination=%s",
        len(ids),
        args.out or "stdout",
    )


if __name__ == "__main__":
    main()
