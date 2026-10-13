#!/usr/bin/env python3
"""Count sessions with a given error-code prefix (default 6xxx) by content name over a date range.

Reads `output/<TENANT>/<date>_setupsession_with_outcome.csv` (`content`, `error_codes` columns). A session
carrying several matching codes counts once per code. Fails loudly if a date file is missing.

Usage:
    python3 count_error_by_content.py --from 2026-10-01 --to 2026-10-10 --tenants SA --prefix 6
"""
import argparse
import csv as std_csv
import logging
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.count_error_by_content")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError(f"--to {end} is before --from {start}")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def count_by_content(rows: list[dict[str, str]], prefix: str) -> Counter:
    """Pure: Counter of (error_code, content) for codes starting with `prefix` and having 4 digits."""
    pattern = re.compile(rf"\b{re.escape(prefix)}\d{{{4 - len(prefix)}}}\b")
    counts: Counter = Counter()
    for r in rows:
        content = (r.get("content") or "").strip() or "(blank)"
        for code in set(pattern.findall(r.get("error_codes") or "")):
            counts[(code, content)] += 1
    return counts


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"content", "error_codes"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def main() -> None:
    init_logging("ctap-smvod-count_error_by_content")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    ap.add_argument("--tenants", default="SA", help="Comma-separated tenant folders under output/")
    ap.add_argument("--prefix", default="6", help="Error-code leading digit(s), e.g. 6 for 6xxx")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{1,3}", args.prefix):
        ap.error("--prefix must be 1-3 digits, e.g. 6")
    for tenant in [t.strip() for t in args.tenants.split(",") if t.strip()]:
        counts: Counter = Counter()
        for d in date_range(args.start, args.end):
            path = OUTPUT_DIR / tenant / f"{d.isoformat()}_setupsession_with_outcome.csv"
            if not path.exists():
                raise FileNotFoundError(path)
            counts.update(count_by_content(read_rows(path), args.prefix))
        out = OUTPUT_DIR / tenant / f"{args.start}_{args.end}_error_{args.prefix}xxx_by_content.csv"
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = std_csv.writer(fh)
            w.writerow(["error_code", "content", "count"])
            for (code, content), n in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1])):
                w.writerow([code, content, n])
        LOGGER.info("%s: %d rows, %d sessions-codes -> %s", tenant, len(counts), sum(counts.values()), out)


if __name__ == "__main__":
    main()
