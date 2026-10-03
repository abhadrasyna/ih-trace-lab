#!/usr/bin/env python3
"""
Extract a compact "position check" CSV from the final
output/YYYY-MM-DD_setupsession_with_outcome.csv report (produced by
merge_session_outcome.py) -- trims the full enriched report down to just
the columns needed to review sessions where playback position may not
have moved: householdId, deviceId, session.clientIp, sessionId,
content_uuid, start_time, error_codes, error_descriptions, state_sequence,
min_position, max_position, position_not_moved.

`content_uuid` (added 17 Jul 2026) is blank for any date whose
SM-VOD aggregate export predates the `playbackURL` column (see
docs/STATUS.md) -- backward-compatible, not an error.

Follows the same trim/select pattern as extract_session_timeline.py, but
keyed off this project's --date DDMMYYYY convention (like
merge_session_outcome.py / merge_ctap_smvod_csv.py) since the source file
is a pipeline output, not an ad-hoc Athena export.

**Filtering defaults (changed 24 Sep 2026, see docs/STATUS.md):**
`--only-not-moved` now defaults to **on** (pass `--no-only-not-moved` to get
every session, the previous default). `--error-code` optionally narrows
further to sessions whose error_codes column contains a given code in this
project's documented 1001-1010 range. Since Step 6c
(`filter_error_code_report.py`) and Step 7 (`correlate_cdn_ips.py`) both
consume this same `output/YYYY-MM-DD_position_report.csv` file expecting
*every* session (not just position-not-moved ones), re-run this script with
`--no-only-not-moved` first if you need the full report for those steps.

Usage:
    python3 extract_position_report.py --date 10072026
    # (--only-not-moved is the default -- see below; use --no-only-not-moved
    # for the old full-report behavior)
    python3 extract_position_report.py --date 10072026 --no-only-not-moved
    python3 extract_position_report.py --date 10072026 --error-code 1003
    python3 extract_position_report.py --date 10072026 \
        --input ../output/2026-07-10_setupsession_with_outcome.csv \
        --out ../output/2026-07-10_position_report.csv
"""
import argparse
from lib import csv_io_compat as csv
import os
import sys

from lib.runtime import investigation_output_dir, snapshot_output_path

DEFAULT_COLUMNS = [
    "householdId", "deviceId", "session.clientIp", "sessionId", "content_uuid",
    "start_time", "error_codes", "error_descriptions", "state_sequence",
    "min_position", "max_position", "position_not_moved",
]

# error_codes cells are a "; "-joined list of every distinct code seen for
# that session (see merge_session_outcome.py's ERROR_FIELDS); --error-code
# restricts to this project's documented 1001-1010 range (see
# queries/QUERY_CATALOG.md) rather than accepting an arbitrary string.
ERROR_CODE_CHOICES = [str(c) for c in range(1001, 1011)]


def _row_has_error_code(row, error_code):
    """Returns True if `error_code` is one of the ';'-joined tokens in
    `row`'s error_codes cell (token match, not exact-string-equals --
    error_codes commonly holds more than one code per session)."""
    codes = {c.strip() for c in row.get("error_codes", "").split(";") if c.strip()}
    return error_code in codes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 10072026")
    default_output_dir = str(investigation_output_dir())
    ap.add_argument("--input", default=None,
                    help="Source CSV (default: <output-dir>/YYYY-MM-DD_setupsession_with_outcome.csv)")
    ap.add_argument("--out", default=None,
                    help="Output CSV path (default: <output-dir>/YYYY-MM-DD_position_report.csv)")
    ap.add_argument("--columns", default=",".join(DEFAULT_COLUMNS),
                    help=f"Comma-separated columns to keep (default: {','.join(DEFAULT_COLUMNS)})")
    ap.add_argument(
        "--only-not-moved", action=argparse.BooleanOptionalAction, default=True,
        help="Keep only rows where position_not_moved == 'true' (default: on -- "
             "pass --no-only-not-moved for the old full-report behavior; note "
             "Step 6c/7 (filter_error_code_report.py/correlate_cdn_ips.py) "
             "expect the full, unfiltered report, see BLUEPRINT.md)")
    ap.add_argument(
        "--error-code", default=None, choices=ERROR_CODE_CHOICES,
        help="Keep only rows whose error_codes column contains this code "
             f"(one of {ERROR_CODE_CHOICES[0]}-{ERROR_CODE_CHOICES[-1]}); "
             "default: no error-code filtering")
    args = ap.parse_args()

    input_path = args.input or snapshot_output_path(args.date, "setupsession_with_outcome", output_dir=default_output_dir)
    if not os.path.exists(input_path):
        print(f"ERROR: input file not found: {input_path} "
              f"(run merge_session_outcome.py first)", file=sys.stderr)
        sys.exit(1)

    columns = [c.strip() for c in args.columns.split(",") if c.strip()]

    with open(input_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        missing = [c for c in columns if c not in available]
        if missing:
            # Treat missing columns as optional/best-effort (same convention
            # as the rest of the pipeline -- e.g. content_uuid, added 17 Jul
            # 2026, won't exist at all in setupsession_with_outcome files
            # generated before playbackURL was added to the SM-VOD export).
            # Warn, don't hard-fail, and just leave those columns blank.
            print(f"WARNING: column(s) {missing} not found in {input_path} "
                  f"-- leaving blank in output. Available columns: {available}",
                  file=sys.stderr)
        if "sessionId" in missing:
            print("ERROR: 'sessionId' is required and missing -- aborting.", file=sys.stderr)
            sys.exit(1)
        # Filter against the full source row (not yet trimmed to --columns)
        # so --only-not-moved/--error-code still work even if a caller's
        # custom --columns list excludes position_not_moved/error_codes.
        source_rows = list(reader)

    if args.only_not_moved:
        source_rows = [
            r for r in source_rows
            if r.get("position_not_moved", "").strip().lower() == "true"
        ]
    if args.error_code:
        source_rows = [r for r in source_rows if _row_has_error_code(r, args.error_code)]

    rows = [{c: row.get(c, "") for c in columns} for row in source_rows]

    out_path = args.out or snapshot_output_path(args.date, "position_report", output_dir=default_output_dir)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows ({len(columns)} columns) to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
