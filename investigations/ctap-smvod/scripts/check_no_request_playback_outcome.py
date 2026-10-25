"""Break one funnel cell down by ``playback_outcome`` (default: license ``no_request`` with no player error).

Answers "are the no_request / no_error sessions EBVS?". Reads the same local files as analyze_drm_funnel.py
and prints a table; ``drm_only`` sessions have no merge row, so they are reported as such.

Usage:
  python investigations/ctap-smvod/scripts/check_no_request_playback_outcome.py --opco GH --date 2026-10-23
"""
from __future__ import annotations

import argparse
from pathlib import Path

from analyze_drm_funnel import (
    DEFAULT_BASE,
    DEFAULT_DRM_BASE,
    flat_error_pairs,
    load_flat_rows,
    load_sessions,
    read_rows,
    require_exports,
)
from lib.drm_exports import read_lrm, read_mdrmfe
from lib.drm_funnel import NO_ERROR, NO_REQUEST, classify_sessions
from lib.drm_outcome_check import outcome_map, tabulate_playback_outcome


def render_table(counts: dict[str, int], license_outcome: str, error_code: str) -> str:
    total = sum(counts.values())
    lines = [f"license_outcome={license_outcome}, error={error_code}: {total} sessions",
             "| playback_outcome | sessions | share |", "|---|---|---|"]
    for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {name} | {n} | {100.0 * n / total:.1f}% |")
    return "\n".join(lines)


def run(opco: str, date: str, base: Path, drm_dir: Path, license_outcome: str, error_code: str) -> str:
    opco_dir = base / opco
    merge_path = opco_dir / f"{date}_setupsession_with_outcome.csv"
    sessions = load_sessions(merge_path)
    rows = read_rows(merge_path)
    if rows and "playback_outcome" not in rows[0]:
        raise ValueError(f"{merge_path.name}: missing required column 'playback_outcome'")
    outcome_by_session = outcome_map(rows)
    require_exports(drm_dir, date)
    flat = flat_error_pairs(load_flat_rows(opco_dir / "error_eventdata_flat" / f"{date}_all.csv"))
    classified = classify_sessions(sessions, read_mdrmfe(drm_dir, date), read_lrm(drm_dir, date), flat)
    counts = tabulate_playback_outcome(classified, outcome_by_session, license_outcome, error_code)
    if not counts:
        raise ValueError(f"no sessions with license_outcome={license_outcome}, error={error_code}")
    return render_table(dict(counts), license_outcome, error_code)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder under --base, e.g. GH")
    ap.add_argument("--date", required=True, help="day YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--drm-dir", type=Path, default=None, help="saved mDRM exports (default data/lightstep/<OPCO>)")
    ap.add_argument("--license-outcome", default=NO_REQUEST, help="funnel license outcome to inspect")
    ap.add_argument("--error", default=NO_ERROR, help="first error code to inspect ('no_error' = none)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-check_no_request_playback_outcome")
    args = parse_args(argv)
    print(run(args.opco, args.date, args.base, args.drm_dir or DEFAULT_DRM_BASE / args.opco,
              args.license_outcome, args.error))


if __name__ == "__main__":
    main()
