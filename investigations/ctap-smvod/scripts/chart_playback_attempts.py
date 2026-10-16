#!/usr/bin/env python3
"""Chart play attempts over one UTC day, one chart per opco (tenant), using `src/lib/charts`.

Attempts follow the Conviva SEI definition: the number of times viewers attempted to start playback in each interval
(https://docs.conviva.ai/sei/video/metric-dictionary/attempts/). Here one attempt = one unique `sessionId` in
`output/<T>/<date>_setupsession_with_outcome.csv`, placed at its earliest `start_time`.

Writes `output/<T>/<date>_playback_attempts.png`; a chart failure for one opco is logged and the others still run.

Usage:
    python3 chart_playback_attempts.py --date 2026-10-14 --tenants SA,GH,ZM --bucket-min 5
"""
import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.concurrency import MINUTES_PER_DAY, minute_label, parse_ts
from src.lib.charts.axes import format_count, padded_range, style_axes
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.header import HeaderCell, Tone, draw_header, header_figure_height, pack_cells
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.chart_playback_attempts")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
X_TICK_STEP_MIN = 180


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"sessionId", "start_time"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def attempts_per_bucket(rows: Sequence[Mapping[str, str]], day: date, bucket_min: int) -> list[int]:
    """Pure: unique sessions per ``bucket_min``-minute UTC bucket of ``day``, each at its earliest start_time.

    Rows without a start_time (outcome-only rows) have no attempt time and are skipped.
    """
    if bucket_min <= 0 or MINUTES_PER_DAY % bucket_min:
        raise ValueError(f"bucket_min must divide {MINUTES_PER_DAY}, got {bucket_min}")
    first_start = {}
    for r in rows:
        sid, ts = (r.get("sessionId") or "").strip(), (r.get("start_time") or "").strip()
        if not ts:
            continue
        if not sid:
            raise ValueError(f"row with start_time {ts} but blank sessionId")
        t = parse_ts(ts)
        if sid not in first_start or t < first_start[sid]:
            first_start[sid] = t
    counts = [0] * (MINUTES_PER_DAY // bucket_min)
    for t in first_start.values():
        if t.date() == day:
            counts[(t.hour * 60 + t.minute) // bucket_min] += 1
    return counts


def header_cells(counts: Sequence[int], bucket_min: int) -> list[HeaderCell]:
    """Pure: total attempts and the busiest bucket."""
    top = max(counts)
    return [
        HeaderCell("ATTEMPTS", format_count(sum(counts)), Tone.POSITIVE),
        HeaderCell(f"PEAK PER {bucket_min} MIN", f"{top} @ {minute_label(counts.index(top) * bucket_min)}"),
    ]


def render_chart(counts: Sequence[int], title: str, bucket_min: int, theme: ChartTheme = DARK) -> bytes:
    """Renders attempts per bucket with a stat header to PNG bytes; raises ChartError on any failure."""
    try:
        family = chart_font_family()
        cells = header_cells(counts, bucket_min)
        fig = new_figure(theme, header_figure_height(pack_cells(cells)))
        draw_header(fig, cells, theme, family)
        ax = fig.add_subplot(111)
        xs = [i * bucket_min for i in range(len(counts))]
        ax.plot(xs, counts, color=theme.green, lw=1.6)
        ax.fill_between(xs, 0, counts, color=theme.green, alpha=theme.fill_alpha_green, lw=0)
        ax.set_xlim(0, MINUTES_PER_DAY - bucket_min)
        ax.set_ylim(*padded_range([0.0, float(max(counts))]))
        ticks = list(range(0, MINUTES_PER_DAY, X_TICK_STEP_MIN))
        ax.set_xticks(ticks, [minute_label(t) for t in ticks])
        ax.yaxis.set_major_formatter(lambda v, _pos: format_count(v))
        style_axes(ax, theme, family)
        fig.text(0.13, 0.02, title, color=theme.faint, fontsize=7.5, family=family)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"playback attempts chart failed: {exc}") from exc


def write_chart(tenant: str, day: date, bucket_min: int, output_dir: Path = OUTPUT_DIR) -> bool:
    """Writes the PNG next to the report CSVs; a ChartError is logged and returns False so other opcos still run."""
    rows = read_rows(output_dir / tenant / f"{day}_setupsession_with_outcome.csv")
    counts = attempts_per_bucket(rows, day, bucket_min)
    untimed = sum(1 for r in rows if not (r.get("start_time") or "").strip())
    LOGGER.info("%s: %d attempts; %d rows without start_time skipped", tenant, sum(counts), untimed)
    title = f"{tenant} play attempts per {bucket_min} min, {day} (UTC)"
    try:
        png = render_chart(counts, title, bucket_min)
    except ChartError:
        LOGGER.exception("%s: chart failed; CSV outputs are unaffected", tenant)
        return False
    out = output_dir / tenant / f"{day}_playback_attempts.png"
    out.write_bytes(png)
    LOGGER.info("%s: wrote %s (%d bytes)", tenant, out, len(png))
    return True


def main() -> None:
    init_logging("ctap-smvod-chart_playback_attempts")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenants", default="SA,GH,ZM", help="Comma-separated tenant folders")
    ap.add_argument("--bucket-min", type=int, default=5, help="Bucket size in minutes (must divide 1440)")
    args = ap.parse_args()
    results = [write_chart(t.strip(), args.date, args.bucket_min, OUTPUT_DIR) for t in args.tenants.split(",") if t.strip()]
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
