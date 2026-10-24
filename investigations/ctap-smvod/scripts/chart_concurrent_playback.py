#!/usr/bin/env python3
"""Chart per-minute concurrent playback for one tenant and UTC day (CH-6 pilot of `src/lib/charts`).

Reads `output/<T>/<date>_concurrent_playback.csv` and `..._summary.csv` (from compute_concurrent_playback.py) and writes
`output/<T>/charts/<date>_concurrent_playback.png`: three lines (csv_only, athena_exact, athena_estimated) plus a stat header
with each view's peak. The athena_estimated line uses the last debug event as the session end -- an estimate.

Usage:
    python3 chart_concurrent_playback.py --date 2026-10-14 --tenants ZA,GH,ZM
"""
import argparse
import csv
import logging
from datetime import date
from pathlib import Path
from typing import Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.concurrency import MINUTES_PER_DAY, minute_label
from src.lib.charts.axes import format_count, padded_range, style_axes
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.header import HeaderCell, Tone, draw_header, header_figure_height, pack_cells
from src.lib.charts.output import write_chart_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.chart_concurrent_playback")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
VIEW_LABELS = {
    "csv_only": "CSV only (lower bound)",
    "athena_exact": "Athena exact",
    "athena_estimated": "Athena + estimated end",
}
X_TICK_STEP_MIN = 180


def read_series(path: Path) -> dict[str, list[int]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != MINUTES_PER_DAY:
        raise ValueError(f"{path}: expected {MINUTES_PER_DAY} minute rows, got {len(rows)}")
    return {v: [int(r[v]) for r in rows] for v in VIEW_LABELS}


def read_summary(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["view"]: r for r in csv.DictReader(fh)}


def header_cells(summary: dict[str, dict[str, str]]) -> list[HeaderCell]:
    """Pure: one peak cell per view (the estimated view is the headline) plus the unresolved-session count."""
    est = summary["athena_estimated"]
    cells = [
        HeaderCell("PEAK (EST. END)", f"{est['peak']} @ {est['peak_minute_utc']}", Tone.POSITIVE),
        HeaderCell("PEAK (ATHENA EXACT)", f"{summary['athena_exact']['peak']} @ {summary['athena_exact']['peak_minute_utc']}"),
        HeaderCell("PEAK (CSV ONLY)", f"{summary['csv_only']['peak']} @ {summary['csv_only']['peak_minute_utc']}", Tone.MUTED),
        HeaderCell("SESSIONS", est["sessions_used"]),
        HeaderCell("END ESTIMATED", est["estimated_ends"], Tone.MUTED),
    ]
    return cells


def render_chart(series: dict[str, list[int]], summary: dict[str, dict[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    """Renders the three-line chart with a stat header to PNG bytes; raises ChartError on any failure."""
    try:
        family = chart_font_family()
        cells = header_cells(summary)
        fig = new_figure(theme, header_figure_height(pack_cells(cells)))
        draw_header(fig, cells, theme, family)
        ax = fig.add_subplot(111)
        xs = list(range(MINUTES_PER_DAY))
        styles = {"athena_estimated": (theme.green, 1.8), "athena_exact": (theme.ink, 1.2), "csv_only": (theme.muted, 1.0)}
        for view, (colour, lw) in styles.items():
            ax.plot(xs, series[view], color=colour, lw=lw, label=VIEW_LABELS[view])
        ax.set_xlim(0, MINUTES_PER_DAY - 1)
        ax.set_ylim(*padded_range([0.0, *(max(s) for s in series.values())]))
        ticks = list(range(0, MINUTES_PER_DAY, X_TICK_STEP_MIN)) + [MINUTES_PER_DAY - 1]
        ax.set_xticks(ticks, [minute_label(t) for t in ticks[:-1]] + ["23:59"])
        ax.yaxis.set_major_formatter(lambda v, _pos: format_count(v))
        style_axes(ax, theme, family)
        ax.legend(frameon=False, labelcolor=theme.muted, prop={"family": family, "size": 8}, loc="upper left")
        fig.text(0.13, 0.02, title, color=theme.faint, fontsize=7.5, family=family)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"concurrent playback chart failed: {exc}") from exc


def write_chart(tenant: str, day: date, output_dir: Path = OUTPUT_DIR) -> bool:
    """Writes the PNG to the tenant's charts folder (CSVs stay in the tenant folder); a ChartError is logged and returns False so other tenants still run."""
    base = output_dir / tenant / f"{day}_concurrent_playback"
    series = read_series(Path(f"{base}.csv"))
    summary = read_summary(Path(f"{base}_summary.csv"))
    title = f"{tenant} concurrent playback sessions per minute, {day} (UTC)"
    try:
        png = render_chart(series, summary, title)
    except ChartError:
        LOGGER.exception("%s: chart failed; CSV outputs are unaffected", tenant)
        return False
    out = write_chart_png(png, output_dir, tenant, f"{day}_concurrent_playback.png")
    LOGGER.info("%s: wrote %s (%d bytes)", tenant, out, len(png))
    return True


def main() -> None:
    init_logging("ctap-smvod-chart_concurrent_playback")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenants", default="ZA,GH,ZM", help="Comma-separated tenant folders")
    args = ap.parse_args()
    for tenant in [t.strip() for t in args.tenants.split(",") if t.strip()]:
        write_chart(tenant, args.date, OUTPUT_DIR)


if __name__ == "__main__":
    main()
