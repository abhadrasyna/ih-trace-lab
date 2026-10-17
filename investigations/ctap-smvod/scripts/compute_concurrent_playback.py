#!/usr/bin/env python3
"""Per-minute concurrent playback for one UTC day, per tenant, from three views of the same day.

Views (all count distinct sessionId; a session is concurrent for every minute its interval overlaps):
  csv_only         `output/<T>/<date>_setupsession_with_outcome.csv` rows with event_start and event_end (lower bound).
  athena_exact     `data/athena/<T>/<date>_session.csv` rows with event_start and event_end (no end -> dropped).
  athena_estimated athena_exact plus, for sessions with no event_end, [first, last] debug event from
                   `data/athena/<T>/<date>_debug_states.csv`. The last event is an estimate, not a real stop.

Writes `output/<T>/<date>_concurrent_playback.csv` (minute, one column per view) and
`output/<T>/<date>_concurrent_playback_summary.csv` (sessions used/dropped/estimated, peak, peak minute).
Fails loudly if an input file or column is missing.

Usage:
    python3 compute_concurrent_playback.py --date 2026-10-14 --tenants ZA,GH,ZM
"""
import argparse
import csv
import logging
from datetime import date
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.concurrency import (
    MINUTES_PER_DAY,
    debug_spans,
    intervals_from_session_rows,
    merge_with_estimates,
    minute_label,
    peak,
    per_minute_concurrency,
)
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.compute_concurrent_playback")
INVESTIGATION_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = INVESTIGATION_DIR / "output"
ATHENA_DIR = INVESTIGATION_DIR / "data" / "athena"
VIEWS = ("csv_only", "athena_exact", "athena_estimated")
SUMMARY_HEADER = ["view", "sessions_used", "sessions_without_end", "estimated_ends", "unresolved", "peak", "peak_minute_utc"]


def read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def build_views(
    outcome_rows: list[dict[str, str]], session_rows: list[dict[str, str]], debug_rows: list[dict[str, str]], day: date
) -> tuple[dict[str, list[int]], list[list[object]]]:
    """Pure: per-view minute series and summary rows."""
    csv_iv, csv_dropped = intervals_from_session_rows(outcome_rows)
    exact, exact_dropped = intervals_from_session_rows(session_rows)
    ids = [r["sessionId"].strip() for r in session_rows]
    merged, estimated, unresolved = merge_with_estimates(exact, ids, debug_spans(debug_rows))
    views = {"csv_only": csv_iv, "athena_exact": exact, "athena_estimated": merged}
    extras = {"csv_only": (csv_dropped, 0, 0), "athena_exact": (exact_dropped, 0, 0), "athena_estimated": (exact_dropped, estimated, unresolved)}
    series = {name: per_minute_concurrency(iv.values(), day) for name, iv in views.items()}
    summary = []
    for name in VIEWS:
        top, minute = peak(series[name])
        dropped, est, unres = extras[name]
        summary.append([name, len(views[name]), dropped, est, unres, top, minute_label(minute)])
    return series, summary


def write_outputs(out_dir: Path, day: date, series: dict[str, list[int]], summary: list[list[object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{day}_concurrent_playback.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["minute_utc", *VIEWS])
        for m in range(MINUTES_PER_DAY):
            w.writerow([minute_label(m), *(series[v][m] for v in VIEWS)])
    with open(out_dir / f"{day}_concurrent_playback_summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(SUMMARY_HEADER)
        w.writerows(summary)


def main() -> None:
    init_logging("ctap-smvod-compute_concurrent_playback")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenants", default="ZA,GH,ZM", help="Comma-separated tenant folders")
    args = ap.parse_args()
    for tenant in [t.strip() for t in args.tenants.split(",") if t.strip()]:
        outcome = read_rows(OUTPUT_DIR / tenant / f"{args.date}_setupsession_with_outcome.csv", {"sessionId", "event_start", "event_end"})
        sessions = read_rows(ATHENA_DIR / tenant / f"{args.date}_session.csv", {"sessionId", "event_start", "event_end"})
        debug = read_rows(ATHENA_DIR / tenant / f"{args.date}_debug_states.csv", {"sessionId", "datetime"})
        series, summary = build_views(outcome, sessions, debug, args.date)
        write_outputs(OUTPUT_DIR / tenant, args.date, series, summary)
        for row in summary:
            LOGGER.info("%s %s: used=%s no_end=%s est=%s unresolved=%s peak=%s @%s", tenant, *row)


if __name__ == "__main__":
    main()
