#!/usr/bin/env python3
"""
Extract distinct sessionId values from a merged report CSV (or any CSV with
a sessionId column) and format them as a SQL `IN (...)` clause, ready to
paste into an Athena query -- e.g. to look up debug_events/unified_sessions
rows for exactly the sessions already present in a given day's report,
instead of scanning a full day's partition.

Usage:
    python3 extract_session_ids.py --input ../output/2026-07-08_setupsession.csv
    python3 extract_session_ids.py --input ../output/2026-07-08_setupsession.csv \
        --column sessionId --out ../queries/exploration/session_ids_08072026.sql

Output (default: stdout) looks like:
    (
      'abr-vod-00e67137-3bd2-42ae-868c-3d072b428fab',
      'abr-vod-02c8b581-96b8-4e60-9e05-9e8995c52f0f',
      ...
    )
"""
import argparse
from lib import csv_io_compat as csv
import sys


def extract_ids(input_path, column="sessionId"):
    """Reads `input_path` and returns the sorted, distinct, non-empty
    values of `column` -- the reusable core of this module, importable
    from other scripts (e.g. `run_athena_debug_events.py`) that need the
    same sessionId list without shelling out to this file's CLI.

    Raises:
        ValueError: If `column` isn't a column in `input_path`.
    """
    with open(input_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if column not in (reader.fieldnames or []):
            raise ValueError(
                f"column '{column}' not found in {input_path}. "
                f"Available columns: {reader.fieldnames}")
        return sorted({row[column] for row in reader if row.get(column)})


def format_in_clause(ids):
    """Renders `ids` as a SQL `IN (...)` clause body, ready to paste into
    an Athena query's `sessionid`/`sessionId` filter."""
    if not ids:
        raise ValueError("cannot render an empty SQL IN clause")
    clause_body = ",\n  ".join("'" + value.replace("'", "''") + "'" for value in ids)
    return f"(\n  {clause_body}\n)\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV file to read sessionIds from")
    ap.add_argument("--column", default="sessionId", help="Column name to extract (default: sessionId)")
    ap.add_argument("--out", default=None, help="Write output here instead of stdout")
    args = ap.parse_args()

    try:
        ids = extract_ids(args.input, args.column)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not ids:
        print(f"ERROR: no non-empty '{args.column}' values found in {args.input}", file=sys.stderr)
        sys.exit(1)

    clause = format_in_clause(ids)

    if args.out:
        with open(args.out, "w") as f:
            f.write(f"-- Generated from {args.input} ({len(ids)} distinct {args.column} values)\n")
            f.write(f"-- Paste the IN (...) block below into an Athena query's {args.column}/sessionid filter\n\n")
            f.write(clause)
        print(f"Wrote {len(ids)} distinct {args.column} values to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(clause)
        print(f"\n({len(ids)} distinct {args.column} values)", file=sys.stderr)


if __name__ == "__main__":
    main()
