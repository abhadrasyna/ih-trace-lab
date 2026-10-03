#!/usr/bin/env python3
"""
Concatenate multiple output/position_report_DDMMYYYY.csv files (produced by
extract_position_report.py) and keep only rows matching a given
error_codes value (default: 1003), writing them out with the exact same
columns as the source files -- no extra columns added.

Usage:
    python3 filter_error_code_report.py --dates 02082026,03082026,04082026,05082026,06082026,07082026,08082026
    python3 filter_error_code_report.py --dates 02082026,03082026 --error-code 1003 \
        --out ../output/position_report_1003_02082026_08082026.csv
"""
import argparse
from lib import csv_io_compat as csv
import os
import sys


def _matches_error_code(cell_value, expected_code):
    tokens = [
        token.strip()
        for chunk in str(cell_value or "").split(";")
        for token in chunk.split(",")
        if token.strip()
    ]
    return expected_code in tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", required=True,
                    help="Comma-separated list of dates in DDMMYYYY format, e.g. 02082026,03082026")
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    ap.add_argument("--input-dir", default=default_dir,
                    help="Directory containing position_report_<date>.csv files (default: ../output)")
    ap.add_argument("--error-code", default="1003",
                    help="Value to match in the error_codes column (default: 1003)")
    ap.add_argument("--out", default=None,
                    help="Output CSV path (default: <input-dir>/position_report_<code>_<first>_<last>.csv)")
    args = ap.parse_args()

    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("ERROR: no dates provided", file=sys.stderr)
        sys.exit(1)

    out_path = args.out or os.path.join(
        args.input_dir, f"position_report_{args.error_code}_{dates[0]}_{dates[-1]}.csv"
    )

    header = None
    rows_written = 0
    matching_rows = []
    for date in dates:
        in_path = os.path.join(args.input_dir, f"position_report_{date}.csv")
        if not os.path.exists(in_path):
            print(f"WARNING: input file not found, skipping: {in_path}", file=sys.stderr)
            continue
        with open(in_path, newline="") as in_fh:
            reader = csv.DictReader(in_fh)
            current_header = reader.fieldnames
            if not current_header:
                print(f"WARNING: header missing in {in_path} -- skipping file", file=sys.stderr)
                continue
            if "error_codes" not in current_header:
                print(f"WARNING: required column 'error_codes' missing in {in_path} -- skipping file", file=sys.stderr)
                continue
            if header is None:
                header = current_header
            elif current_header != header:
                print(f"WARNING: column mismatch in {in_path}, expected {header}, "
                      f"got {current_header} -- skipping file", file=sys.stderr)
                continue
            for row in reader:
                if _matches_error_code(row.get("error_codes"), args.error_code):
                    matching_rows.append(row)
                    rows_written += 1

    if header is None:
        print("ERROR: no valid input files processed", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w", newline="") as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(matching_rows)

    print(f"Wrote {rows_written} rows (error_codes={args.error_code}) to {out_path}")


if __name__ == "__main__":
    main()
