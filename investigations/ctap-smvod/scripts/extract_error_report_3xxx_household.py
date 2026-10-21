#!/usr/bin/env python3
"""Extract every session of one household whose error_codes contain a 3xxx code (exact 4-digit token, ^3\\d{3}$)
from output/<TENANT>/<date>_setupsession_with_outcome.csv over a date range, keeping the same columns as
extract_error_report_1xxx_6xxx.py (including is_wv). Writes one CSV: <from>_<to>_error_report_3xxx_<household8>.csv.

Reads existing pipeline outputs only -- never fires Athena/Lightstep. Aborts if a date file is missing or no row matches.

Usage:
    python3 extract_error_report_3xxx_household.py --household-id <householdId> \
        --tenant ZA --from 01102026 --to 19102026
"""
import argparse
import logging
import os
import re
import sys

from extract_error_report_1xxx_6xxx import DEFAULT_COLUMNS, dates_in_range, read_source, write_csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.runtime import range_output_path, snapshot_output_path
from lib.webview import is_wv_cell
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.extract_error_report_3xxx_household")
ERROR_CODE_RE = re.compile(r"^3\d{3}$")
ARTIFACT = "error_report_3xxx"


def row_has_3xxx(row: dict) -> bool:
    """True if any ';'/','-separated token of error_codes is an exact 4-digit code starting with 3."""
    cell = row.get("error_codes", "") or ""
    tokens = (t.strip() for chunk in cell.split(";") for t in chunk.split(","))
    return any(ERROR_CODE_RE.match(t) for t in tokens)


def filter_rows(source_rows: list[dict], household_id: str, columns: list[str]) -> list[dict]:
    """Rows of `household_id` with a 3xxx error, projected to `columns` (is_wv computed from the user agent)."""
    if not household_id:
        raise ValueError("household_id must not be empty")
    return [
        {c: r.get(c, "") for c in columns} | ({"is_wv": is_wv_cell(r)} if "is_wv" in columns else {})
        for r in source_rows if r.get("householdId") == household_id and row_has_3xxx(r)
    ]


def main():
    init_logging("ctap-smvod-extract_error_report_3xxx_household")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--household-id", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--from", dest="date_from", required=True, help="Range start DDMMYYYY")
    ap.add_argument("--to", dest="date_to", required=True, help="Range end DDMMYYYY, inclusive")
    ap.add_argument("--out", default=None, help="Output path override")
    args = ap.parse_args()

    try:
        dates = dates_in_range(args.date_from, args.date_to)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    inputs = {d: snapshot_output_path(d, "setupsession_with_outcome", tenant=args.tenant) for d in dates}
    missing = [d for d, p in inputs.items() if not os.path.exists(p)]
    if missing:
        print(f"ERROR: setupsession_with_outcome.csv missing for: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for path in inputs.values():
        rows += filter_rows(read_source(path), args.household_id, DEFAULT_COLUMNS)
    rows.sort(key=lambda r: r["start_time"])
    if not rows:
        print(f"ERROR: no 3xxx rows for household {args.household_id!r} in {args.date_from}..{args.date_to}", file=sys.stderr)
        sys.exit(1)
    out_path = args.out or range_output_path(args.date_from, args.date_to, ARTIFACT, tag=args.household_id[:8],
                                             tenant=args.tenant)
    write_csv(out_path, DEFAULT_COLUMNS, rows)
    print(f"Wrote {len(rows)} rows to {out_path}", file=sys.stderr)
    LOGGER.info("Completed extract_error_report_3xxx_household rows=%d out=%s", len(rows), out_path)


if __name__ == "__main__":
    main()
