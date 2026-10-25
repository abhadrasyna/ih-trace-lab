"""Daily DRM session funnel for one OpCo: sessions -> DRM request -> license outcome -> downstream error.

Reads only local files (no Athena or Lightstep):
  <base>/<OPCO>/<date>_setupsession_with_outcome.csv           (required)
  <base>/<OPCO>/error_eventdata_flat/<date>_all.csv            (optional)
  <drm-dir>/<date>_mdrmfe.csv and <date>_mdrm-lrm.csv (+ hourly parts)  (required)
Writes <base>/<OPCO>/<date>_drm_funnel.csv and <date>_drm_funnel.md.

Usage:
  python investigations/ctap-smvod/scripts/analyze_drm_funnel.py --opco ZA --date 2026-10-23
"""
from __future__ import annotations

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from lib.drm_exports import LRM, MDRMFE, export_paths, read_lrm, read_mdrmfe
from lib.drm_funnel import FunnelResult, FunnelRow, SessionInput, build_funnel

csv.field_size_limit(10**9)

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_drm_funnel")
DEFAULT_BASE = Path(__file__).resolve().parents[1] / "output"
DEFAULT_DRM_BASE = Path(__file__).resolve().parents[1] / "data" / "lightstep"
CSV_COLUMNS = [
    "opco", "date", "source", "kind", "drm_bucket", "license_outcome", "error_group", "sessions",
]
STAGE_LABELS = [
    ("sessions", "Sessions"),
    ("drm_requested", "Asked for a DRM license"),
    ("license_success", "License succeeded (incl. after retry)"),
    ("license_failed", "License failed"),
    ("errored", "Ended in a player error"),
    ("drm_only", "Of which `drm_only` (not in the CTAP/SMVOD merge)"),
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_sessions(path: Path) -> list[SessionInput]:
    if not path.exists():
        raise FileNotFoundError(f"merge file not found: {path}")
    rows = read_rows(path)
    missing = [c for c in ("sessionId", "error_codes") if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{path.name}: missing required column(s) {missing}")
    return [SessionInput(r["sessionId"].strip(), r["error_codes"]) for r in rows]


def load_flat_errors(path: Path) -> list[tuple[str, str]]:
    """Optional: an absent flat error file means no extra error rows."""
    if not path.exists():
        LOGGER.warning("%s missing; downstream errors come from the merge file only", path)
        return []
    rows = read_rows(path)
    missing = [c for c in ("sessionId", "errorcode") if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{path.name}: missing required column(s) {missing}")
    return [(r["sessionId"].strip(), r["errorcode"]) for r in rows]


def require_exports(drm_dir: Path, date: str) -> None:
    for kind in (MDRMFE, LRM):
        if not export_paths(drm_dir, date, kind):
            raise FileNotFoundError(f"mDRM export not found: {drm_dir / f'{date}_{kind}.csv'}")


def pct(part: int, total: int) -> str:
    return f"{100.0 * part / total:.1f}%" if total else "n/a"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(r) + " |" for r in rows)
    return lines


def _pivot(rows: list[FunnelRow], row_field: str, col_field: str) -> tuple[list[str], list[list[str]]]:
    cols = sorted({getattr(r, col_field) for r in rows})
    cells: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cells[getattr(r, row_field)][getattr(r, col_field)] += r.sessions
    body = []
    for key in sorted(cells):
        counts = [cells[key][c] for c in cols]
        body.append([key, *map(str, counts), str(sum(counts))])
    return [row_field, *cols, "total"], body


def render_markdown(opco: str, date: str, result: FunnelResult) -> str:
    totals = result.totals
    total = totals["sessions"]
    lines = [f"# DRM funnel — {opco} — {date}", ""]
    lines += ["## Stages", ""]
    lines += _table(
        ["Stage", "Sessions", "Share of sessions"],
        [[label, str(totals[key]), pct(totals[key], total)] for key, label in STAGE_LABELS],
    )
    if totals["drm_only"]:
        lines += ["", f"**Note:** {totals['drm_only']} session(s) appear only in the mDRM exports (`source=drm_only`) "
                      "and are counted in the totals above."]
    sections = [
        ("DRM type split", "drm_bucket", "kind"),
        ("License outcome per DRM type", "drm_bucket", "license_outcome"),
        ("Downstream error per license outcome", "license_outcome", "error_group"),
    ]
    for title, row_field, col_field in sections:
        header, body = _pivot(result.rows, row_field, col_field)
        lines += ["", f"## {title}", ""] + _table(header, body)
    return "\n".join(lines) + "\n"


def write_outputs(out_dir: Path, opco: str, date: str, result: FunnelResult) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{date}_drm_funnel.csv"
    md_path = out_dir / f"{date}_drm_funnel.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows({c: getattr(r, c) for c in CSV_COLUMNS} for r in result.rows)
    md_path.write_text(render_markdown(opco, date, result), encoding="utf-8")
    return csv_path, md_path


def run(opco: str, date: str, base: Path, drm_dir: Path) -> FunnelResult:
    opco_dir = base / opco
    sessions = load_sessions(opco_dir / f"{date}_setupsession_with_outcome.csv")
    require_exports(drm_dir, date)
    flat = load_flat_errors(opco_dir / "error_eventdata_flat" / f"{date}_all.csv")
    result = build_funnel(opco, date, sessions, read_mdrmfe(drm_dir, date), read_lrm(drm_dir, date), flat)
    distinct = len({s.session_id for s in sessions if s.session_id})
    if result.totals["sessions"] != distinct + result.totals["drm_only"]:
        raise ValueError(f"{opco} {date}: funnel sessions do not reconcile to the merge session count")
    write_outputs(opco_dir, opco, date, result)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder under --base, e.g. ZA")
    ap.add_argument("--date", required=True, help="day YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--drm-dir", type=Path, default=None,
                    help="folder with the saved mDRM exports (default data/lightstep/<OPCO>)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-analyze_drm_funnel")
    args = parse_args(argv)
    result = run(args.opco, args.date, args.base, args.drm_dir or DEFAULT_DRM_BASE / args.opco)
    LOGGER.info("%s %s: %s", args.opco, args.date, result.totals)


if __name__ == "__main__":
    main()
