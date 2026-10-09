#!/usr/bin/env python3
"""Count rows of a flattened error-eventdata CSV (see flatten_error_eventdata.py) grouped by chosen columns.

Read-only; prints to stdout. One table per `--by` group; `--by errorcode,net_effectivetype` is a crosstab.

Usage:
    python3 summarize_error_eventdata.py --flat ../output/ZM/2026-10-04_error_eventdata_flat.csv \
        --by errorcode --by errorcode,shaka_message --by errorcode,is_wv --by errorcode,shaka_url_host
"""
import argparse
import logging
from collections import Counter

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.summarize_error_eventdata")


def group_counts(rows: list[dict[str, str]], columns: list[str]) -> Counter:
    """Pure: row count per distinct tuple of `columns`. Raises ValueError on an unknown column."""
    if rows:
        missing = [c for c in columns if c not in rows[0]]
        if missing:
            raise ValueError(f"unknown columns: {missing}")
    return Counter(tuple(r[c] or "(blank)" for c in columns) for r in rows)


def render(columns: list[str], counts: Counter, total: int) -> str:
    lines = [f"\n== {' x '.join(columns)} (rows={total}) =="]
    for key, n in counts.most_common():
        lines.append(f"{n:5d}  {100.0 * n / total:5.1f}%  {' | '.join(key)}")
    return "\n".join(lines)


def main() -> None:
    init_logging("ctap-smvod-summarize_error_eventdata")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flat", required=True, help="Flattened *_error_eventdata_flat.csv")
    ap.add_argument("--by", action="append", required=True, help="Comma-separated columns to group by (repeatable)")
    args = ap.parse_args()

    with open(args.flat, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for spec in args.by:
        columns = [c.strip() for c in spec.split(",") if c.strip()]
        print(render(columns, group_counts(rows, columns), len(rows)))


if __name__ == "__main__":
    main()
