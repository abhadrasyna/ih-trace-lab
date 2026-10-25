"""Daily DRM session funnel for one OpCo: sessions -> DRM request -> license outcome -> downstream error.

Reads only local files (no Athena or Lightstep):
  <base>/<OPCO>/<date>_setupsession_with_outcome.csv           (required)
  <base>/<OPCO>/error_eventdata_flat/<date>_all.csv            (optional)
  <drm-dir>/<date>_mdrmfe.csv and <date>_mdrm-lrm.csv (+ hourly parts)  (required)
Writes <base>/<OPCO>/<date>_drm_funnel.csv and <date>_drm_funnel.md, plus three charts under
<base>/<OPCO>/charts/ embedded in the markdown (a chart failure is logged and its link is left out).

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
from lib.drm_funnel import (
    NAMED_ERRORS,
    NO_ERROR,
    FunnelResult,
    FunnelRow,
    SessionInput,
    build_funnel,
    first_error_by_session,
)
from lib.drm_funnel_charts import build_chart_specs, chart_filename, render_chart
from lib.drm_funnel_subcategory import subcategory_by_session
from run_3016_subcategory_report import first_row_by_session, read_optional

from src.lib.charts.errors import ChartError
from src.lib.charts.output import write_chart_png

csv.field_size_limit(10**9)

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_drm_funnel")
DEFAULT_BASE = Path(__file__).resolve().parents[1] / "output"
DEFAULT_DRM_BASE = Path(__file__).resolve().parents[1] / "data" / "lightstep"
CSV_COLUMNS = [
    "opco", "date", "source", "kind", "drm_bucket", "license_outcome", "error_group", "error_code", "subcategory", "sessions",
]
OUTCOMES = ("success", "retry_then_success", "failed", "no_request")
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


def load_flat_rows(path: Path) -> list[dict[str, str]]:
    """Optional: an absent flat error file means no extra error rows."""
    if not path.exists():
        LOGGER.warning("%s missing; downstream errors come from the merge file only", path)
        return []
    rows = read_rows(path)
    missing = [c for c in ("sessionId", "errorcode") if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{path.name}: missing required column(s) {missing}")
    return rows


def flat_error_pairs(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
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


def outcome_by_code(rows: list[FunnelRow], codes: list[str] | None = None) -> dict[str, dict[str, int]]:
    """Sessions per error code and license outcome; ``codes`` limits (and keeps empty) the listed codes."""
    cells: dict[str, dict[str, int]] = {c: dict.fromkeys(OUTCOMES, 0) for c in codes or []}
    for r in rows:
        if r.error_code == NO_ERROR or (codes is not None and r.error_code not in cells):
            continue
        cells.setdefault(r.error_code, dict.fromkeys(OUTCOMES, 0))[r.license_outcome] += r.sessions
    return cells


def _outcome_cells(counts: dict[str, int]) -> list[str]:
    total = sum(counts.values())
    return [f"{counts[o]} ({pct(counts[o], total)})" for o in OUTCOMES]


def error_code_section(rows: list[FunnelRow]) -> list[str]:
    cells = outcome_by_code(rows)
    errored = sum(sum(c.values()) for c in cells.values())
    body = [[code, str(sum(c.values())), pct(sum(c.values()), errored), *_outcome_cells(c)]
            for code, c in sorted(cells.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))]
    lines = ["", "## Ended in error by code", "",
             "Each session is counted under its first error code only.", ""]
    lines += _table(["error_code", "sessions", "share of errored", *OUTCOMES], body or [["none", "0", "n/a", "", "", "", ""]])
    return lines


def named_error_section(rows: list[FunnelRow]) -> list[str]:
    cells = outcome_by_code(rows, list(NAMED_ERRORS))
    body = [[code, str(sum(c.values())), *_outcome_cells(c)] for code, c in cells.items()]
    lines = ["", "## 3014 / 3015 / 3016 by license outcome", ""]
    lines += _table(["error_code", "sessions", *OUTCOMES], body)
    for code, c in cells.items():
        total = sum(c.values())
        if total:
            top = max(OUTCOMES, key=lambda o: c[o])
            lines.append("")
            word = "most" if 2 * c[top] > total else "the largest share of"
            lines.append(f"Reading: {word} {code} sessions had license outcome `{top}` ({pct(c[top], total)}).")
    return lines


def subcategory_section(rows: list[FunnelRow]) -> list[str]:
    """Sub-category by license outcome for 3014/3015/3016 sessions only; total equals the named-code table."""
    cells: dict[str, dict[str, int]] = {}
    for r in rows:
        if r.error_code in NAMED_ERRORS:
            cells.setdefault(r.subcategory, dict.fromkeys(OUTCOMES, 0))[r.license_outcome] += r.sessions
    body = [[sub, str(sum(c.values())), *_outcome_cells(c)]
            for sub, c in sorted(cells.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))]
    lines = ["", "## 3014/3015/3016 by sub-category", ""]
    lines += _table(["sub-category", "sessions", *OUTCOMES], body or [["none", "0", "", "", "", ""]])
    lines += ["", f"Total: {sum(sum(c.values()) for c in cells.values())} sessions (equals the 3014/3015/3016 table above)."]
    return lines


def render_markdown(opco: str, date: str, result: FunnelResult, charts: dict[str, str] | None = None) -> str:
    """``charts`` maps a chart name to its file name under ``charts/`` for relative embedding."""
    totals = result.totals
    total = totals["sessions"]
    lines = [f"# DRM funnel — {opco} — {date}", ""]
    if charts:
        for name, filename in charts.items():
            lines += [f"![{name.replace('_', ' ')}](charts/{filename})", ""]
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
    lines += error_code_section(result.rows) + named_error_section(result.rows) + subcategory_section(result.rows)
    return "\n".join(lines) + "\n"


def write_charts(base: Path, opco: str, date: str, result: FunnelResult, absolute: bool = False) -> dict[str, str]:
    """Writes each chart PNG; a ``ChartError`` is logged and that chart is skipped."""
    written: dict[str, str] = {}
    for spec in build_chart_specs(opco, date, result.rows, absolute=absolute):
        try:
            png = render_chart(spec)
        except ChartError as exc:
            LOGGER.error("%s %s: chart %s failed: %s", opco, date, spec.name, exc)
            continue
        filename = chart_filename(date, spec.name)
        write_chart_png(png, base, opco, filename)
        written[spec.name] = filename
    return written


def write_outputs(
    out_dir: Path, opco: str, date: str, result: FunnelResult, charts: dict[str, str] | None = None
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{date}_drm_funnel.csv"
    md_path = out_dir / f"{date}_drm_funnel.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows({c: getattr(r, c) for c in CSV_COLUMNS} for r in result.rows)
    md_path.write_text(render_markdown(opco, date, result, charts), encoding="utf-8")
    return csv_path, md_path


def load_subcategories(
    opco_dir: Path, opco: str, date: str, sessions: list[SessionInput],
    flat_rows: list[dict[str, str]], flat: list[tuple[str, str]],
) -> dict[str, str]:
    """Sub-category per 3014/3015/3016 session; a missing position report only warns (join is enrichment)."""
    setup = read_optional(opco_dir / f"{date}_setupsession_with_outcome.csv")
    pos = read_optional(opco_dir / f"{date}_position_report.csv")
    first_errors = first_error_by_session(sessions, flat)
    return subcategory_by_session(
        first_errors, flat_rows, first_row_by_session(setup), first_row_by_session(pos), opco, date
    )


def run(opco: str, date: str, base: Path, drm_dir: Path, absolute: bool = False) -> FunnelResult:
    opco_dir = base / opco
    sessions = load_sessions(opco_dir / f"{date}_setupsession_with_outcome.csv")
    require_exports(drm_dir, date)
    flat_rows = load_flat_rows(opco_dir / "error_eventdata_flat" / f"{date}_all.csv")
    flat = flat_error_pairs(flat_rows)
    subcategories = load_subcategories(opco_dir, opco, date, sessions, flat_rows, flat)
    result = build_funnel(
        opco, date, sessions, read_mdrmfe(drm_dir, date), read_lrm(drm_dir, date), flat, subcategories
    )
    distinct = len({s.session_id for s in sessions if s.session_id})
    if result.totals["sessions"] != distinct + result.totals["drm_only"]:
        raise ValueError(f"{opco} {date}: funnel sessions do not reconcile to the merge session count")
    write_outputs(opco_dir, opco, date, result, write_charts(base, opco, date, result, absolute))
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder under --base, e.g. ZA")
    ap.add_argument("--date", required=True, help="day YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--drm-dir", type=Path, default=None,
                    help="folder with the saved mDRM exports (default data/lightstep/<OPCO>)")
    ap.add_argument("--absolute", action="store_true",
                    help="draw the license_outcome chart as raw counts instead of share of each DRM type")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-analyze_drm_funnel")
    args = parse_args(argv)
    result = run(args.opco, args.date, args.base, args.drm_dir or DEFAULT_DRM_BASE / args.opco, args.absolute)
    LOGGER.info("%s %s: %s", args.opco, args.date, result.totals)


if __name__ == "__main__":
    main()
