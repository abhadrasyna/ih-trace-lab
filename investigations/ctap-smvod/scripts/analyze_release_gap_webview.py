#!/usr/bin/env python3
"""Checks whether sessions with a Lightstep SetupSession but no Release are Android WebView sessions.

Inputs for one tenant and UTC day (all under the investigation root):
  - `output/<T>/<date>_ebvs_release_coverage.csv`        from `analyze_ebvs_release_coverage.py` (`has_setup` / `has_release`)
  - `output/<T>/<date>_setupsession_with_outcome.csv`    carries `raw_user_agent` / `Platform` for the WebView check

Only sessions with `has_setup=true` and `has_release=false` are judged. A session without a user agent is "unknown", never "non-wv".
Prints a table per `playback_outcome` and writes `output/<T>/<date>_release_gap_webview.csv` (one row per gap session).

Usage:
    python3 analyze_release_gap_webview.py --date 2026-10-30 --tenant ZA
"""
import argparse
import csv
import logging
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path

from compare_lightstep_athena_sessions import read_rows
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.webview import is_wv_cell

from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_release_gap_webview")
ROOT = Path(__file__).resolve().parent.parent
DETAIL_COLUMNS = ["sessionId", "playback_outcome", "is_wv"]
SUMMARY_COLUMNS = ["playback_outcome", "gap_sessions", "wv", "non_wv", "unknown", "wv_pct_of_known"]
UA_COLUMNS = ["sessionId", "raw_user_agent", "Platform"]


def release_gap_webview(coverage: Iterable[Mapping[str, str]], setup_rows: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    """Pure: one row per session with a SetupSession but no Release, with `is_wv` ("true"/"false"/"" when no user agent).

    Setup rows are keyed by sessionId; the first row with a user agent wins.
    """
    wv_by_id: dict[str, str] = {}
    for row in setup_rows:
        sid = (row.get("sessionId") or "").strip()
        cell = is_wv_cell(dict(row))
        if sid and (sid not in wv_by_id or (not wv_by_id[sid] and cell)):
            wv_by_id[sid] = cell
    return [
        {"sessionId": r["sessionId"], "playback_outcome": r["playback_outcome"], "is_wv": wv_by_id.get(r["sessionId"], "")}
        for r in coverage
        if r["has_setup"] == "true" and r["has_release"] != "true"
    ]


def summarize(detail: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Pure: per-outcome WebView counts (largest outcome first) plus a TOTAL row; the pct is over sessions with a known user agent."""
    counts: dict[str, Counter] = {}
    for row in detail:
        counts.setdefault(row["playback_outcome"], Counter())[row["is_wv"]] += 1
    ordered = sorted(counts.items(), key=lambda item: (-sum(item[1].values()), item[0]))
    total: Counter = Counter()
    for _, c in ordered:
        total += c
    summary = []
    for outcome, c in [*ordered, ("TOTAL", total)]:
        known = c["true"] + c["false"]
        summary.append({
            "playback_outcome": outcome, "gap_sessions": str(sum(c.values())), "wv": str(c["true"]), "non_wv": str(c["false"]),
            "unknown": str(c[""]), "wv_pct_of_known": f"{100 * c['true'] / known:.1f}" if known else "",
        })
    return summary


def format_table(summary: Sequence[Mapping[str, str]]) -> str:
    widths = {c: max([len(c), *(len(r[c]) for r in summary)]) for c in SUMMARY_COLUMNS}
    lines = ["  ".join(c.ljust(widths[c]) for c in SUMMARY_COLUMNS)]
    lines += ["  ".join(r[c].ljust(widths[c]) for c in SUMMARY_COLUMNS) for r in summary]
    return "\n".join(lines)


def write_detail(path: Path, detail: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        writer.writerows(detail)


def main() -> int:
    init_logging("ctap-smvod-analyze_release_gap_webview")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", default="ZA")
    ap.add_argument("--root", type=Path, default=ROOT, help="Investigation root (default: ctap-smvod)")
    args = ap.parse_args()

    out_dir = args.root / "output" / args.tenant
    coverage = read_rows(out_dir / f"{args.date}_ebvs_release_coverage.csv", ["sessionId", "playback_outcome", "has_setup", "has_release"])
    setup_rows = read_rows(out_dir / f"{args.date}_setupsession_with_outcome.csv", UA_COLUMNS)

    detail = release_gap_webview(coverage, setup_rows)
    out = out_dir / f"{args.date}_release_gap_webview.csv"
    write_detail(out, detail)
    print(f"{args.tenant} {args.date}: {len(detail)} sessions with SetupSession but no Release")
    print(format_table(summarize(detail)))
    LOGGER.info("Wrote %s (%d rows)", out, len(detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
