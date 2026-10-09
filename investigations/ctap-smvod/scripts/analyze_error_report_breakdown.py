#!/usr/bin/env python3
"""Break down a YYYY-MM-DD_error_report_1xxx_6xxx.csv: error-code frequency,
is_wv split, error code x is_wv, position_not_moved share, top devices/
households/state sequences, hourly distribution, and (optionally) the error
rate against all sessions in the matching *_setupsession_with_outcome.csv.

Read-only; prints to stdout, writes nothing.

Usage:
    python3 analyze_error_report_breakdown.py \
        --error-report ../output/SA/2026-10-09_error_report_1xxx_6xxx.csv \
        --outcome-report ../output/SA/2026-10-09_setupsession_with_outcome.csv
"""
import argparse
import logging
import re
from collections import Counter

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.webview import is_wv
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_error_report_breakdown")

REQUIRED_COLUMNS = ("sessionId", "error_codes", "is_wv")
_CODE_SPLIT = re.compile(r"[,;|\s]+")


def is_true(value: str) -> bool:
    return (value or "").strip().lower() == "true"


def split_codes(value: str) -> list[str]:
    return [c for c in _CODE_SPLIT.split((value or "").strip()) if c]


def pct(part: int, total: int) -> str:
    return f"{100.0 * part / total:.1f}%" if total else "n/a"


def hour_of(start_time: str) -> str:
    """'2026-10-09 00:00:39.100 UTC' -> '00'."""
    parts = (start_time or "").split(" ")
    return parts[1][:2] if len(parts) > 1 else "(no start_time)"


def breakdown(rows: list[dict[str, str]]) -> dict:
    """Pure aggregation over error-report rows."""
    missing = [c for c in REQUIRED_COLUMNS if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"error report is missing required columns: {missing}")
    codes, codes_wv, codes_non_wv = Counter(), Counter(), Counter()
    hours, devices, households, states = Counter(), Counter(), Counter(), Counter()
    wv_rows = not_moved = 0
    for row in rows:
        wv = is_true(row["is_wv"])
        wv_rows += wv
        not_moved += is_true(row.get("position_not_moved", ""))
        for code in split_codes(row["error_codes"]) or ["(none)"]:
            codes[code] += 1
            (codes_wv if wv else codes_non_wv)[code] += 1
        hours[hour_of(row.get("start_time", ""))] += 1
        devices[row.get("deviceId", "")] += 1
        households[row.get("householdId", "")] += 1
        states[row.get("state_sequence", "")] += 1
    return {
        "total": len(rows), "wv": wv_rows, "not_moved": not_moved,
        "codes": codes, "codes_wv": codes_wv, "codes_non_wv": codes_non_wv,
        "hours": hours, "devices": devices, "households": households, "states": states,
        "unique_sessions": len({r["sessionId"] for r in rows}),
    }


def error_rate(outcome_rows: list[dict[str, str]], error_sessions: set[str]) -> dict:
    """Share of all sessions (and wv sessions) that appear in the error report."""
    if outcome_rows and not {"sessionId", "raw_user_agent"} <= set(outcome_rows[0]):
        raise ValueError("outcome report must have sessionId and raw_user_agent columns")
    total = len(outcome_rows)
    wv_total = sum(1 for r in outcome_rows if is_wv(r))
    wv_err = sum(1 for r in outcome_rows if is_wv(r) and r.get("sessionId") in error_sessions)
    err = sum(1 for r in outcome_rows if r.get("sessionId") in error_sessions)
    return {"total": total, "errors": err, "wv_total": wv_total, "wv_errors": wv_err}


def _top(title: str, counter: Counter, total: int, n: int) -> None:
    print(f"\n== {title} ==")
    for key, count in counter.most_common(n):
        print(f"{count:6d}  {pct(count, total):>6}  {key}")


def read_rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def print_report(stats: dict, rate: dict | None, top: int) -> None:
    total = stats["total"]
    print(f"Error rows: {total} (unique sessions: {stats['unique_sessions']})")
    print(f"is_wv true: {stats['wv']} ({pct(stats['wv'], total)}) | false: {total - stats['wv']}")
    print(f"position_not_moved true: {stats['not_moved']} ({pct(stats['not_moved'], total)})")
    if rate:
        print(f"Error sessions / all sessions: {rate['errors']}/{rate['total']} ({pct(rate['errors'], rate['total'])})")
        print(f"WV error sessions / all WV sessions: {rate['wv_errors']}/{rate['wv_total']} "
              f"({pct(rate['wv_errors'], rate['wv_total'])})")
    _top("Error code frequency (share of rows; a row may hold several codes)", stats["codes"], total, top)
    print("\n== Error code x is_wv ==")
    for code, count in stats["codes"].most_common(top):
        wv, non = stats["codes_wv"][code], stats["codes_non_wv"][code]
        print(f"{code:>8}  total={count:5d}  wv={wv:5d} ({pct(wv, count)})  non_wv={non:5d}")
    _top("Top state sequences", stats["states"], total, top)
    _top("Top devices (deviceId)", stats["devices"], total, top)
    _top("Top households", stats["households"], total, top)
    print("\n== Errors by hour (UTC) ==")
    for hour in sorted(stats["hours"]):
        print(f"{hour}  {stats['hours'][hour]:5d}")


def main() -> None:
    init_logging("ctap-smvod-analyze_error_report_breakdown")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--error-report", required=True, help="Path to *_error_report_1xxx_6xxx.csv")
    ap.add_argument("--outcome-report", default=None, help="Optional *_setupsession_with_outcome.csv for rates")
    ap.add_argument("--top", type=int, default=10, help="Rows per breakdown")
    args = ap.parse_args()

    error_rows = read_rows(args.error_report)
    stats = breakdown(error_rows)
    rate = None
    if args.outcome_report:
        rate = error_rate(read_rows(args.outcome_report), {r["sessionId"] for r in error_rows})
    print_report(stats, rate, args.top)


if __name__ == "__main__":
    main()
