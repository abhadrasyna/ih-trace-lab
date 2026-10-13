#!/usr/bin/env python3
"""Count sessions and unique households with a given error-code prefix (default 6xxx) by content name.

Reads `output/<TENANT>/<date>_setupsession_with_outcome.csv` (`content`, `error_codes`, `householdId`, `sessionId`)
over a date range and writes `<from>_<to>_error_6xxx_by_content.csv` (per error code) and `..._rollup.csv` (all codes
combined, each session/household counted once per content). Fails loudly if a date file or column is missing.

Usage:
    python3 count_error_by_content.py --from 2026-10-01 --to 2026-10-10 --tenants SA --prefix 6
"""
import argparse
import csv as std_csv
import logging
import re
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


Hit = tuple[str, str, str, str]  # (error_code, content, sessionId, householdId)


def collect_hits(rows: list[dict[str, str]], prefix: str) -> list[Hit]:
    """Pure: one hit per (session, matching 4-digit error code starting with `prefix`)."""
    pattern = re.compile(rf"\b{re.escape(prefix)}\d{{{4 - len(prefix)}}}\b")
    hits: list[Hit] = []
    for r in rows:
        content = (r.get("content") or "").strip() or "(blank)"
        for code in sorted(set(pattern.findall(r.get("error_codes") or ""))):
            sid, hh = (r.get("sessionId") or "").strip(), (r.get("householdId") or "").strip()
            if not sid or not hh:
                raise ValueError(f"blank sessionId/householdId on an error row (code {code}, content {content!r})")
            hits.append((code, content, sid, hh))
    return hits


def aggregate(hits: list[Hit], by_code: bool) -> dict[tuple[str, str], tuple[int, int]]:
    """Pure: (error_code|'ALL', content) -> (distinct sessions, distinct households)."""
    sessions: dict[tuple[str, str], set[str]] = {}
    households: dict[tuple[str, str], set[str]] = {}
    for code, content, sid, hh in hits:
        key = (code if by_code else "ALL", content)
        sessions.setdefault(key, set()).add(sid)
        households.setdefault(key, set()).add(hh)
    return {k: (len(sessions[k]), len(households[k])) for k in sessions}


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"content", "error_codes", "householdId", "sessionId"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def write_table(path: Path, header: list[str], agg: dict[tuple[str, str], tuple[int, int]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = std_csv.writer(fh)
        w.writerow(header)
        for (code, content), (n, hh) in sorted(agg.items(), key=lambda kv: (kv[0][0], -kv[1][1], -kv[1][0], kv[0][1])):
            w.writerow([code, content, n, hh])


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
        hits: list[Hit] = []
        for d in date_range(args.start, args.end):
            path = OUTPUT_DIR / tenant / f"{d.isoformat()}_setupsession_with_outcome.csv"
            if not path.exists():
                raise FileNotFoundError(path)
            hits.extend(collect_hits(read_rows(path), args.prefix))
        stem = OUTPUT_DIR / tenant / f"{args.start}_{args.end}_error_{args.prefix}xxx_by_content"
        header = ["error_code", "content", "sessions", "unique_households"]
        write_table(Path(f"{stem}.csv"), header, aggregate(hits, by_code=True))
        write_table(Path(f"{stem}_rollup.csv"), header, aggregate(hits, by_code=False))
        LOGGER.info("%s: %d hits -> %s(.csv|_rollup.csv)", tenant, len(hits), stem)


if __name__ == "__main__":
    main()
