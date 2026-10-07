#!/usr/bin/env python3
"""
Combine split Lightstep CSV exports (Step 1 pre-processing, ahead of
run_pipeline.py).

Background: a Lightstep span-samples export caps out at ~1000 rows. When a
day's sample count exceeds that, the export has to be pulled in multiple
time-windowed parts (e.g. 12hr/12hr) instead of one 24hr file, and is saved
as:

    YYYY-MM-DD_NN_ctap.csv
    YYYY-MM-DD_NN_smvod.csv
    YYYY-MM-DD_NN_smvod-ts.csv

(NN = 01, 02, ... any count/width). This script detects any such numbered
parts in --input-dir, combines each (date, artifact) group back into the
single canonical file run_pipeline.py/merge_ctap_smvod_csv.py already
expect:

    YYYY-MM-DD_ctap.csv
    YYYY-MM-DD_smvod.csv
    YYYY-MM-DD_smvod-ts.csv

Days that were exported the old way (no _NN_ in the filename) are left
completely untouched -- this script only ever acts on days that actually
have numbered parts; it never replaces or re-derives an already-whole file.

Rows are merged by column NAME (csv.DictReader/DictWriter), not by raw line
concatenation/position. This matters because real exports have been seen
where one part's column order differs from another's (same column set,
shuffled order) -- a positional concatenation would silently misalign data
in that case. If two parts of the same group have different column SETS
(not just order), that's treated as a real mismatch and raises an error
rather than silently dropping/blank-filling columns.

Usage:
    python3 combine_lightstep_parts.py
    python3 combine_lightstep_parts.py --date 2026-10-03
    python3 combine_lightstep_parts.py --dry-run
    python3 combine_lightstep_parts.py --force       # overwrite existing combined files
    python3 combine_lightstep_parts.py --remove-parts # delete part files after a successful combine
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from collections import defaultdict

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.combine_lightstep_parts")

ARTIFACTS = ("ctap", "smvod-ts", "smvod")  # smvod-ts before smvod: longer alternative first
PART_FILE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<part>\d+)_(?P<artifact>" + "|".join(ARTIFACTS) + r")\.csv$"
)

DEFAULT_INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "lightstep")


class ColumnMismatchError(ValueError):
    """Raised when two parts of the same (date, artifact) group have different column sets."""


def find_part_groups(input_dir, only_date=None):
    """Scan input_dir for YYYY-MM-DD_NN_<artifact>.csv files.

    Returns {(date, artifact): [(part_num, path), ...]} sorted by part_num.
    """
    groups = defaultdict(list)
    for name in sorted(os.listdir(input_dir)):
        match = PART_FILE_RE.match(name)
        if not match:
            continue
        date = match.group("date")
        if only_date and date != only_date:
            continue
        part_num = int(match.group("part"))
        artifact = match.group("artifact")
        groups[(date, artifact)].append((part_num, os.path.join(input_dir, name)))
    for key in groups:
        groups[key].sort(key=lambda item: item[0])
    return groups


def combine_parts(part_paths):
    """Merge a list of CSV paths (same logical columns, any order) by column name.

    Returns (fieldnames, rows). Raises ColumnMismatchError if any part's column
    set differs from the first part's.
    """
    fieldnames = None
    rows = []
    for path in part_paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            part_fields = list(reader.fieldnames or [])
            if fieldnames is None:
                fieldnames = part_fields
            elif set(part_fields) != set(fieldnames):
                only_here = set(part_fields) - set(fieldnames)
                only_first = set(fieldnames) - set(part_fields)
                raise ColumnMismatchError(
                    f"{path}: column set differs from {part_paths[0]} "
                    f"(only in this part: {sorted(only_here)}, only in first part: {sorted(only_first)})"
                )
            rows.extend(dict(row) for row in reader)
    return fieldnames, rows


def write_combined(out_path, fieldnames, rows):
    # Write to a same-directory temp file, then atomically rename into place. If this process is
    # interrupted (Ctrl-C, disk full, bad row) partway through, out_path either doesn't exist yet or
    # still holds its previous complete contents -- never a truncated file that a later run's
    # "already exists, skip" check would mistake for a finished combine.
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, out_path)


def main():
    init_logging("ctap-smvod-combine_lightstep_parts")
    LOGGER.info("Starting combine_lightstep_parts")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory holding the Lightstep CSV exports")
    ap.add_argument("--date", default=None, help="Only process this date (YYYY-MM-DD); default: all dates found")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing combined file if one is already present")
    ap.add_argument("--remove-parts", action="store_true", help="Delete the _NN_ part files after a successful combine")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be combined without writing/deleting anything")
    args = ap.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    groups = find_part_groups(input_dir, only_date=args.date)

    if not groups:
        msg = f"No numbered part files (_NN_) found in {input_dir}" + (f" for date {args.date}" if args.date else "")
        print(msg)
        LOGGER.info(msg)
        return

    combined_count = 0
    skipped_count = 0
    for (date, artifact), parts in sorted(groups.items()):
        out_path = os.path.join(input_dir, f"{date}_{artifact}.csv")
        part_paths = [p for _, p in parts]
        part_labels = [f"{num:02d}" for num, _ in parts]

        if os.path.exists(out_path) and not args.force:
            print(f"SKIP {date}_{artifact}: {out_path} already exists (parts: {part_labels}); use --force to overwrite")
            skipped_count += 1
            continue

        fieldnames, rows = combine_parts(part_paths)

        if args.dry_run:
            print(f"DRY-RUN would combine {date}_{artifact} parts {part_labels} ({len(rows)} rows) -> {out_path}")
            continue

        write_combined(out_path, fieldnames, rows)
        print(f"Combined {date}_{artifact} parts {part_labels} ({len(rows)} rows) -> {out_path}")
        LOGGER.info("Combined date=%s artifact=%s parts=%s rows=%d out=%s", date, artifact, part_labels, len(rows), out_path)
        combined_count += 1

        if args.remove_parts:
            for part_path in part_paths:
                os.remove(part_path)
            print(f"  removed {len(part_paths)} part file(s)")

    LOGGER.info("Completed combine_lightstep_parts combined=%d skipped=%d", combined_count, skipped_count)


if __name__ == "__main__":
    try:
        main()
    except ColumnMismatchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
