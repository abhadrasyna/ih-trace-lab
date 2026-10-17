#!/usr/bin/env python3
"""
Combine one tenant's 1xxx error sessions over a date range into a single CSV (a leading `date` column
holds the ISO date). Reuses extract_error_report_1xxx's filter; reads existing
output/<TENANT>/YYYY-MM-DD_setupsession_with_outcome.csv files only -- never fires Athena/Lightstep.
Aborts naming every missing input so a partial result is never written.

Usage:
    python3 combine_error_report_1xxx_csv.py --tenant ZA --from 01102026 --to 11102026
    # -> output/ZA/<range>_error_report_1xxx_combined.csv
"""
import argparse
import logging
import os
import sys

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

import extract_error_report_1xxx as ext
import extract_error_report_1xxx_6xxx as base
from lib.runtime import ddmmyyyy_to_date, range_output_path, snapshot_output_path

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.combine_error_report_1xxx_csv")

ARTIFACT = "error_report_1xxx_combined"


def combine_rows(per_date: dict[str, list[dict]]) -> list[dict]:
    """Flatten {iso_date: rows} into one list, prefixing each row with its date."""
    return [{"date": d} | r for d, rows in per_date.items() for r in rows]


def main() -> None:
    init_logging("ctap-smvod-combine_error_report_1xxx_csv")
    LOGGER.info("Starting combine_error_report_1xxx_csv")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tenant", required=True, help="Tenant code, e.g. ZA")
    ap.add_argument("--from", dest="date_from", required=True, help="Range start DDMMYYYY")
    ap.add_argument("--to", dest="date_to", required=True, help="Range end DDMMYYYY, inclusive")
    ap.add_argument("--output-dir", default=None, help="Root holding <TENANT>/ output folders (default: investigation output dir)")
    ap.add_argument("--columns", default=",".join(base.DEFAULT_COLUMNS), help="Comma-separated columns to keep")
    args = ap.parse_args()

    columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    tenant = args.tenant.strip().upper()
    out_dir = ext.tenant_dir(tenant, args.output_dir)
    try:
        dates = base.dates_in_range(args.date_from, args.date_to)
        missing = ext.missing_inputs([tenant], dates, args.output_dir)
        if missing:
            raise ValueError("setupsession_with_outcome.csv missing:\n  " + "\n  ".join(missing))
        per_date = {ddmmyyyy_to_date(d).isoformat(): ext.filter_rows(
            base.read_source(snapshot_output_path(d, "setupsession_with_outcome", output_dir=out_dir)), columns)
            for d in dates}
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    rows = combine_rows(per_date)
    out_path = range_output_path(args.date_from, args.date_to, ARTIFACT, output_dir=out_dir)
    base.write_csv(out_path, ["date", *columns], rows)
    print(f"{tenant}: wrote {len(rows)} rows across {len(per_date)} date(s) to {out_path}", file=sys.stderr)
    LOGGER.info("Completed combine_error_report_1xxx_csv tenant=%s rows=%d out=%s", tenant, len(rows), out_path)


if __name__ == "__main__":
    main()
