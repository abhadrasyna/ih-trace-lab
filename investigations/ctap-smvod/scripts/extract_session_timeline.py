#!/usr/bin/env python3
"""
Extract a compact event timeline (content, event_type, event_start,
event_end, endreason) from a raw `unified_sessions` CSV export -- that
table returns multiple rows per session (one per player lifecycle
event_type: PLAY, REQUEST_VIEWING, BUFFERING, ...), and this trims it down
to just the columns useful for eyeballing what happened during a session,
sorted chronologically by event_start.

Usage:
    python3 extract_session_timeline.py --input ../queries/exploration/3e27ae96_session.csv
    python3 extract_session_timeline.py --input ../queries/exploration/3e27ae96_session.csv \
        --out ../queries/exploration/3e27ae96_timeline.csv
    python3 extract_session_timeline.py --input ../queries/exploration/3e27ae96_session.csv \
        --columns event_type,event_start,event_end,content,endreason
"""
import argparse
import logging
from lib import csv_io_compat as csv
import sys
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.extract_session_timeline")

DEFAULT_COLUMNS = ["event_type", "event_start", "event_end", "content", "endreason"]


def main():
    init_logging("ctap-smvod-extract_session_timeline")
    LOGGER.info("Starting extract_session_timeline")
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Raw unified_sessions CSV export")
    ap.add_argument("--out", default=None, help="Write trimmed CSV here instead of stdout")
    ap.add_argument("--columns", default=",".join(DEFAULT_COLUMNS),
                    help=f"Comma-separated columns to keep (default: {','.join(DEFAULT_COLUMNS)})")
    ap.add_argument("--sort-by", default="event_start", help="Column to sort chronologically by (default: event_start)")
    args = ap.parse_args()

    columns = [c.strip() for c in args.columns.split(",") if c.strip()]

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        missing = [c for c in columns if c not in available]
        if missing:
            print(f"ERROR: column(s) {missing} not found in {args.input}. "
                  f"Available columns: {available}", file=sys.stderr)
            sys.exit(1)
        rows = [{c: row.get(c, "") for c in columns} for row in reader]

    if args.sort_by in columns:
        rows.sort(key=lambda r: r.get(args.sort_by, ""))

    out_f = open(args.out, "w", newline="") if args.out else sys.stdout
    writer = csv.DictWriter(out_f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    if args.out:
        out_f.close()
        print(f"Wrote {len(rows)} rows ({len(columns)} columns) to {args.out}", file=sys.stderr)

    LOGGER.info(
        "Completed extract_session_timeline rows=%d destination=%s",
        len(rows),
        args.out or "stdout",
    )


if __name__ == "__main__":
    main()
