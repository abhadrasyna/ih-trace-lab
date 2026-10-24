"""Daily 3014/3015/3016 sub-category report: write a summary CSV and a per-event CSV per OpCo and day.

Reads only local files under `<base>/<OPCO>/` (no Athena or Lightstep):
  error_eventdata_flat/<date>_all.csv, <date>_setupsession_with_outcome.csv, <date>_position_report.csv

Usage:
  python investigations/ctap-smvod/scripts/run_3016_subcategory_report.py --opco ZA --date 2026-10-22
  python investigations/ctap-smvod/scripts/run_3016_subcategory_report.py --opco ZA --from 2026-10-20 --to 2026-10-22
  python investigations/ctap-smvod/scripts/run_3016_subcategory_report.py --opco ZA --date 2026-10-22 --drm

`--drm` also reads the saved mDRM exports in data/lightstep/<OPCO>/ (see docs/lightstep-drm-exports.md), adds the DRM
columns to the events CSV and writes <date>_subcategory_device_summary.csv.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date as Date, timedelta
from pathlib import Path

from build_3016_drm_device_summary import SUMMARY_COLUMNS as DEVICE_SUMMARY_COLUMNS, summarise
from build_3016_drm_link import DRM_COLUMNS, link
from build_3016_subcategory_events import build_events
from lib.drm_exports import read_cdm, read_lrm, read_mdrmfe
from build_3016_subcategory_summary import SUMMARY_COLUMNS, build_summary

csv.field_size_limit(10**9)

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_3016_subcategory_report")
ERROR_CODES = {"3014", "3015", "3016"}
EVENT_COLUMNS = [
    "date", "opco", "subcategory", "errorcode", "datetime", "householdId", "deviceId", "sessionId",
    "content_uuid", "externalPackageId", "segment_file", "event_position", "player_phase", "pipeline_status",
    "browser", "device_model", "os", "user_agent", "session_max_position", "join_setup", "join_position",
    "hh_repeat_events", "content_distinct_hh",
]
DEFAULT_BASE = Path(__file__).resolve().parents[1] / "output"
DEFAULT_DRM_BASE = Path(__file__).resolve().parents[1] / "data" / "lightstep"


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def first_row_by_session(rows: list[dict]) -> dict[str, dict]:
    """Map sessionId to its first row; rows with an empty sessionId are skipped."""
    out: dict[str, dict] = {}
    for r in rows:
        sid = r.get("sessionId", "")
        if sid and sid not in out:
            out[sid] = r
    return out


def select_errors(flat_rows: list[dict]) -> list[dict]:
    return [r for r in flat_rows if r.get("errorcode") in ERROR_CODES]


def reconcile(errors: list[dict], events: list[dict], summary: list[dict]) -> None:
    """Raise unless events and summary totals equal the flat file's 3014/3015/3016 row count."""
    summed = sum(r["events"] for r in summary)
    if len(events) != len(errors) or summed != len(errors):
        raise ValueError(
            f"reconciliation failed: flat rows={len(errors)}, events rows={len(events)}, summary total={summed}"
        )


def build_day(flat_rows: list[dict], setup_rows: list[dict], pos_rows: list[dict], opco: str, day: str):
    errors = select_errors(flat_rows)
    events = build_events(errors, first_row_by_session(setup_rows), first_row_by_session(pos_rows), opco, day)
    summary = build_summary(events)
    reconcile(errors, events, summary)
    return events, summary


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def read_optional(path: Path) -> list[dict]:
    """Join inputs are enrichment only (sub-categories come from the flat file), so a missing file warns
    on stderr and the `join_setup`/`join_position` columns record it as false, per the SUB-4 spec."""
    if not path.exists():
        print(f"WARNING: {path} missing; join columns will be false", file=sys.stderr)
        return []
    return read_rows(path)


def add_drm(events: list[dict], drm_dir: Path, day: str) -> list[dict]:
    """Add the DRM columns from the saved Lightstep exports; the row count must not change."""
    linked = link(events, read_mdrmfe(drm_dir, day), read_cdm(drm_dir, day), read_lrm(drm_dir, day))
    if len(linked) != len(events):
        raise ValueError(f"DRM link changed the row count: {len(events)} -> {len(linked)}")
    return linked


def run_day(opco: str, day: str, base: Path, out: Path | None, drm_dir: Path | None = None) -> tuple[int, int]:
    opco_dir = base / opco
    flat_path = opco_dir / "error_eventdata_flat" / f"{day}_all.csv"
    if not flat_path.exists():
        raise FileNotFoundError(f"flat error file not found: {flat_path}")
    setup = read_optional(opco_dir / f"{day}_setupsession_with_outcome.csv")
    pos = read_optional(opco_dir / f"{day}_position_report.csv")
    events, summary = build_day(read_rows(flat_path), setup, pos, opco, day)
    out_dir = out or opco_dir / "subcategory_3016"
    write_csv(out_dir / f"{day}_subcategory_summary.csv", SUMMARY_COLUMNS, summary)
    columns = EVENT_COLUMNS
    if drm_dir is not None:
        events = add_drm(events, drm_dir, day)
        columns = EVENT_COLUMNS + DRM_COLUMNS
        write_csv(out_dir / f"{day}_subcategory_device_summary.csv", DEVICE_SUMMARY_COLUMNS, summarise(events))
    write_csv(out_dir / f"{day}_subcategory_events.csv", columns, events)
    return len(events), len(summary)


def date_range(start: str, end: str) -> list[str]:
    d0, d1 = Date.fromisoformat(start), Date.fromisoformat(end)
    if d1 < d0:
        raise ValueError(f"--to {end} is before --from {start}")
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder under --base, e.g. ZA")
    ap.add_argument("--date", help="single day YYYY-MM-DD")
    ap.add_argument("--from", dest="date_from", help="range start YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", help="range end YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default <base>/<OPCO>/subcategory_3016)")
    ap.add_argument("--drm", action="store_true", help="add DRM device columns and write the device summary")
    ap.add_argument("--drm-dir", type=Path, default=None,
                    help="folder with the saved mDRM Lightstep exports (default data/lightstep/<OPCO>)")
    args = ap.parse_args(argv)
    if args.drm_dir and not args.drm:
        ap.error("--drm-dir needs --drm")
    if bool(args.date) == bool(args.date_from or args.date_to) or bool(args.date_from) != bool(args.date_to):
        ap.error("give either --date, or both --from and --to")
    return args


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-run_3016_subcategory_report")
    args = parse_args(argv)
    days = [args.date] if args.date else date_range(args.date_from, args.date_to)
    for day in days:
        drm_dir = (args.drm_dir or DEFAULT_DRM_BASE / args.opco) if args.drm else None
        n_events, n_rows = run_day(args.opco, day, args.base, args.out, drm_dir)
        LOGGER.info("%s %s: %d events, %d summary rows", args.opco, day, n_events, n_rows)


if __name__ == "__main__":
    main()
