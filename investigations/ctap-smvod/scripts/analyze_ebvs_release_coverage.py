#!/usr/bin/env python3
"""Checks, per Athena playback outcome, how many sessions have a SetupSession and a Release span in Lightstep (EBVS Release-gap hypothesis).

Inputs for one tenant and UTC day (all under the investigation root):
  - `data/athena/<T>/<date>_session.csv`            Athena sessions with `playback_outcome` (EBVS, DESTROY, PLAYER_ERROR, ...)
  - `data/lightstep/<T>/<date>_smvod.csv`           Lightstep SetupSession sessionIds (`export_lightstep_day.py --kinds smvod`)
  - `data/lightstep/<T>/<date>_smvod-release.csv`   Lightstep Release sessionIds (`export_lightstep_day.py --kinds smvod-release`)
The next day's `smvod-release` file is also read when present, because a late session releases after midnight UTC.

The non-EBVS outcomes are the control: a Release gap that shows up for every outcome is a Lightstep coverage problem, not an EBVS finding.
Only sessions with a SetupSession in Lightstep can be judged, so `release_missing_pct` is taken over those.

Prints one table row per outcome and writes `output/<T>/<date>_ebvs_release_coverage.csv` (one row per Athena session with `has_setup` / `has_release`).

Usage:
    python3 analyze_ebvs_release_coverage.py --date 2026-10-30 --tenant ZA
"""
import argparse
import csv
import logging
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path

from compare_lightstep_athena_sessions import read_rows, unique_ids
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_ebvs_release_coverage")
ROOT = Path(__file__).resolve().parent.parent
DETAIL_COLUMNS = ["sessionId", "playback_outcome", "has_setup", "has_release"]
SUMMARY_COLUMNS = ["playback_outcome", "sessions", "with_setup", "with_release", "setup_without_release", "release_missing_pct"]
MISSING_OUTCOME = "(blank)"


def classify(rows: Iterable[Mapping[str, str]], setup_ids: set[str], release_ids: set[str]) -> list[dict[str, str]]:
    """Pure: one detail row per distinct Athena sessionId with its outcome and whether Lightstep saw its SetupSession and Release.

    A sessionId seen with two different outcomes raises (the Athena export is one row per session).
    """
    outcomes: dict[str, str] = {}
    for row in rows:
        sid = (row.get("sessionId") or "").strip()
        if not sid:
            continue
        outcome = (row.get("playback_outcome") or "").strip() or MISSING_OUTCOME
        if outcomes.setdefault(sid, outcome) != outcome:
            raise ValueError(f"sessionId {sid} has two playback outcomes: {outcomes[sid]!r} and {outcome!r}")
    return [
        {"sessionId": sid, "playback_outcome": outcome, "has_setup": str(sid in setup_ids).lower(), "has_release": str(sid in release_ids).lower()}
        for sid, outcome in sorted(outcomes.items())
    ]


def summarize(detail: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Pure: per-outcome counts, largest outcome first; `release_missing_pct` is over sessions that have a Lightstep SetupSession."""
    groups: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in detail:
        groups[row["playback_outcome"]].append(row)
    summary = []
    for outcome, rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        with_setup = [r for r in rows if r["has_setup"] == "true"]
        missing = [r for r in with_setup if r["has_release"] != "true"]
        pct = f"{100 * len(missing) / len(with_setup):.1f}" if with_setup else ""
        summary.append({
            "playback_outcome": outcome, "sessions": str(len(rows)), "with_setup": str(len(with_setup)),
            "with_release": str(sum(r["has_release"] == "true" for r in rows)), "setup_without_release": str(len(missing)),
            "release_missing_pct": pct,
        })
    return summary


def format_table(summary: Sequence[Mapping[str, str]]) -> str:
    widths = {c: max(len(c), *(len(r[c]) for r in summary)) for c in SUMMARY_COLUMNS} if summary else {c: len(c) for c in SUMMARY_COLUMNS}
    lines = ["  ".join(c.ljust(widths[c]) for c in SUMMARY_COLUMNS)]
    lines += ["  ".join(r[c].ljust(widths[c]) for c in SUMMARY_COLUMNS) for r in summary]
    return "\n".join(lines)


def load_release_ids(directory: Path, day: date) -> tuple[set[str], list[Path]]:
    """Release sessionIds from the day's file (required) and the next day's file (used when present)."""
    paths = [directory / f"{day}_smvod-release.csv"]
    next_day = directory / f"{day + timedelta(days=1)}_smvod-release.csv"
    if next_day.exists():
        paths.append(next_day)
    ids: set[str] = set()
    for path in paths:
        found, _ = unique_ids(read_rows(path, ["sessionId"]))
        ids |= found
    return ids, paths


def write_detail(path: Path, detail: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        writer.writerows(detail)


def main() -> int:
    init_logging("ctap-smvod-analyze_ebvs_release_coverage")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", default="ZA")
    ap.add_argument("--root", type=Path, default=ROOT, help="Investigation root (default: ctap-smvod)")
    args = ap.parse_args()

    athena_rows = read_rows(args.root / "data" / "athena" / args.tenant / f"{args.date}_session.csv", ["sessionId", "playback_outcome"])
    lightstep_dir = args.root / "data" / "lightstep" / args.tenant
    setup_ids, _ = unique_ids(read_rows(lightstep_dir / f"{args.date}_smvod.csv", ["sessionId"]))
    release_ids, release_paths = load_release_ids(lightstep_dir, args.date)

    detail = classify(athena_rows, setup_ids, release_ids)
    out = args.root / "output" / args.tenant / f"{args.date}_ebvs_release_coverage.csv"
    write_detail(out, detail)
    print(f"{args.tenant} {args.date}: {len(detail)} Athena sessions, {len(setup_ids)} Lightstep SetupSession ids, "
          f"{len(release_ids)} Release ids from {', '.join(p.name for p in release_paths)}")
    print(format_table(summarize(detail)))
    LOGGER.info("Wrote %s (%d rows)", out, len(detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
