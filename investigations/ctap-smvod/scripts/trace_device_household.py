#!/usr/bin/env python3
"""Trace one device/household across the daily ctap-smvod CSVs under `output/<TENANT>/`.

Reads `<date>_setupsession_with_outcome.csv` (playback attempts: sessions, content, outcome) and
`error_eventdata_flat/<date>_all.csv` (player errors) and prints: operations (span names), playback
attempts per content/outcome, and failures by error code / shaka category / media error type / content.
Error events are joined to content via sessionId. Fails loudly if a required file or column is missing.

Usage:
    python3 trace_device_household.py --device-id f1062d7b... --tenant ZA --from 2026-10-18 --to 2026-10-19
"""
import argparse
import logging
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.trace_device_household")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
SESSION_COLS = ("householdId", "deviceId", "sessionId", "content", "span_name", "error_flag", "playback_outcome",
                "error_codes", "start_time")
ERROR_COLS = ("datetime", "deviceId", "householdId", "sessionId", "errorcode", "shaka_category", "shaka_error_name", "pipeline_status")


def filter_rows(rows: list[dict], device_id: str) -> list[dict]:
    """Rows belonging to the device; raises if a required column is missing."""
    if rows and "deviceId" not in rows[0]:
        raise ValueError("input rows have no deviceId column")
    return [r for r in rows if r["deviceId"] == device_id]


def session_content_map(session_rows: list[dict]) -> dict[str, str]:
    """First non-blank content per sessionId; blank sessionIds are skipped; conflicting contents raise."""
    out: dict[str, str] = {}
    for r in session_rows:
        sid, content = r["sessionId"], r["content"]
        if not sid or not content:
            continue
        if out.setdefault(sid, content) != content:
            raise ValueError(f"session {sid} has conflicting content: {out[sid]!r} vs {content!r}")
    return out


def summarize(session_rows: list[dict], error_rows: list[dict]) -> dict:
    """Aggregate operations, playback attempts and failures for already-filtered rows."""
    content_of = session_content_map(session_rows)
    errors_by_content: dict[str, Counter] = defaultdict(Counter)
    for e in error_rows:
        errors_by_content[content_of.get(e["sessionId"], "(no session match)")][e["errorcode"]] += 1
    return {
        "households": sorted({r["householdId"] for r in session_rows + error_rows if r["householdId"]}),
        "operations": Counter(r["span_name"] or "(blank)" for r in session_rows),
        "playback_sessions": len({r["sessionId"] for r in session_rows if r["sessionId"]}),
        "outcomes": Counter(r["playback_outcome"] or "(blank)" for r in session_rows),
        "attempts_by_content": Counter(content_of.values()),
        "error_codes": Counter(e["errorcode"] for e in error_rows),
        "shaka_categories": Counter(e["shaka_category"] for e in error_rows),
        "shaka_error_names": Counter(e["shaka_error_name"] for e in error_rows),
        "pipeline_status": Counter(e["pipeline_status"] or "(blank)" for e in error_rows),
        "errors_by_content": errors_by_content,
        "error_sessions": len({e["sessionId"] for e in error_rows if e["sessionId"]}),
    }


def read_csv(path: Path, required: tuple[str, ...]) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        return list(reader)


def daterange(start: date, end: date):
    while start <= end:
        yield start
        start += timedelta(days=1)


def print_report(device_id: str, s: dict) -> None:
    print(f"device: {device_id}\nhouseholds: {s['households']}")
    print(f"playback sessions (unique): {s['playback_sessions']} | sessions with errors (unique): {s['error_sessions']}")
    print("note: operations/outcomes count rows; attempts-by-content counts unique sessions")
    for title, key in (("operations (span_name)", "operations"), ("playback outcome", "outcomes"),
                       ("attempts by content", "attempts_by_content"), ("error codes", "error_codes"),
                       ("shaka category", "shaka_categories"), ("shaka error name", "shaka_error_names"), ("pipeline status", "pipeline_status")):
        print(f"\n{title}:")
        for k, v in s[key].most_common():
            print(f"  {v:4d}  {k}")
    print("\nerrors by content:")
    for content, codes in sorted(s["errors_by_content"].items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {sum(codes.values()):4d}  {content}  {dict(codes)}")


def main():
    init_logging("ctap-smvod-trace_device_household")
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    args = ap.parse_args()
    if args.start > args.end:
        ap.error("--from must be <= --to")
    sessions, errors = [], []
    for d in daterange(args.start, args.end):
        base = OUTPUT_DIR / args.tenant
        sessions += filter_rows(read_csv(base / f"{d}_setupsession_with_outcome.csv", SESSION_COLS), args.device_id)
        errors += filter_rows(read_csv(base / "error_eventdata_flat" / f"{d}_all.csv", ERROR_COLS), args.device_id)
    print_report(args.device_id, summarize(sessions, errors))
    LOGGER.info("Completed trace_device_household sessions=%d errors=%d", len(sessions), len(errors))


if __name__ == "__main__":
    main()
