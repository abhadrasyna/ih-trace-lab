#!/usr/bin/env python3
"""Flatten an Athena `e6auj7k7_ccl_debug_events` CSV export into one flat
row per input row, extracting the nested `eventdata` JSON into first-class
columns keyed by `eventid` (state, position, errorcode, content_id, ...).

Processes the input CSV **one row at a time** (`csv.DictReader` streaming,
no full-file load into memory) via the pure `flatten_row()` function in
`scripts/lib/debug_event_parser.py` -- keep all actual parsing logic there;
this file is just argument parsing + I/O wiring.

Output columns are a fixed superset across every known eventid (blank for
columns that don't apply to a given row's eventid), so the result loads
cleanly as a single CSV/DataFrame for column-by-column analysis (e.g.
comparing against the CTAP/SM-VOD Lightstep columns this project already
tracks -- see docs/STATUS.md's Athena-vs-Lightstep comparison).

Usage:
    python3 flatten_debug_events.py --input ../queries/exploration/<hhid>/e6auj7k7_ccl_debug_events.csv \
        --out ../queries/exploration/<hhid>/e6auj7k7_ccl_debug_events_flat.csv
"""
import argparse
from lib import csv_io_compat as csv
import sys

from lib.debug_event_parser import COMMON_FIELDS, EXTRA_FIELDS_BY_EVENTID, flatten_row

# Fixed, stable output column order: common fields first, then every
# eventid-specific field (deduplicated, first-seen order) so the header
# never changes shape between runs regardless of which eventids happen to
# appear in a given input file.
def _all_fieldnames():
    seen = list(COMMON_FIELDS)
    seen_set = set(seen)
    for fields in EXTRA_FIELDS_BY_EVENTID.values():
        for f in fields:
            if f not in seen_set:
                seen.append(f)
                seen_set.add(f)
    return seen


ALL_FIELDNAMES = _all_fieldnames()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Path to raw e6auj7k7_ccl_debug_events CSV export")
    ap.add_argument("--out", required=True, help="Path to write the flattened CSV")
    args = ap.parse_args()

    total = 0
    unhandled_eventids = set()
    with open(args.input, newline="", encoding="utf-8") as infile, \
         open(args.out, "w", newline="", encoding="utf-8") as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=ALL_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            total += 1
            flat = flatten_row(row)
            if flat.get("eventid") not in EXTRA_FIELDS_BY_EVENTID:
                unhandled_eventids.add(flat.get("eventid"))
            writer.writerow(flat)

    print(f"Flattened {total} rows -> {args.out}", file=sys.stderr)
    if unhandled_eventids:
        print(f"WARNING: {len(unhandled_eventids)} eventid(s) had no dedicated extractor "
              f"(common fields + raw_eventdata only): {sorted(unhandled_eventids)}", file=sys.stderr)


if __name__ == "__main__":
    main()
