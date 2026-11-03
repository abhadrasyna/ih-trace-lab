"""Day-wise line chart of error arrival counts per code (used by count_error_arrival_rate.py --chart).

With many codes (e.g. `--codes all`) one line each is unreadable, so only the `top` codes by total count get a line;
the rest are summed into one muted "other (N codes)" line, so the chart total still matches the data.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Mapping

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.charts.axes import format_count, padded_range, style_axes
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.charts.title import draw_title

DailyCounts = Mapping[date, int]
LINE_COLOURS = ("#60a5fa", "#f472b6", "#a78bfa", "#26b3a0", "#f59e0b", "#ef5350", "#d4a373", "#34d399")
DEFAULT_TOP = len(LINE_COLOURS)
OTHER_RE = re.compile(r"other \(\d+ codes\)")


def top_series(per_code: Mapping[str, DailyCounts], top: int) -> dict[str, dict[date, int]]:
    """Top `top` codes by total count keep their own series; the remainder are summed into 'other (N codes)'."""
    if not 1 <= top <= DEFAULT_TOP:
        raise ValueError(f"top must be 1..{DEFAULT_TOP} (one distinct colour per line)")
    if not per_code:
        raise ValueError("no codes to chart")
    ranked = sorted(per_code, key=lambda c: (-sum(per_code[c].values()), c))
    out = {c: dict(per_code[c]) for c in ranked[:top]}
    rest = ranked[top:]
    if rest:
        days = sorted({d for c in rest for d in per_code[c]})
        out[f"other ({len(rest)} codes)"] = {d: sum(per_code[c].get(d, 0) for c in rest) for d in days}
    return out


def render_arrival_chart(per_code: Mapping[str, DailyCounts], metric: str, title: str, top: int = DEFAULT_TOP,
                         theme: ChartTheme = DARK) -> bytes:
    """PNG bytes of one line per code (top-N + other) over the days; raises ChartError on any failure."""
    try:
        series = top_series(per_code, top)
        seen = [d for s in series.values() for d in s]
        first, last = min(seen), max(seen)
        days = [first + timedelta(n) for n in range((last - first).days + 1)]  # a day with no errors plots as 0
        if len(days) < 2:
            raise ValueError("need at least 2 days to draw a line")
        family = chart_font_family()
        fig = new_figure(theme)
        draw_title(fig, title, f"{metric} per UTC day, all selected tenants combined", theme, family)
        ax = fig.add_subplot(111)
        for i, (code, daily) in enumerate(series.items()):
            colour = theme.muted if OTHER_RE.fullmatch(code) else LINE_COLOURS[i % len(LINE_COLOURS)]
            ax.plot(days, [daily.get(d, 0) for d in days], color=colour, lw=1.6, marker="o", ms=3, label=code)
        ax.set_ylim(*padded_range([0.0, *(v for s in series.values() for v in s.values())]))
        ax.yaxis.set_major_formatter(lambda v, _pos: format_count(v))
        style_axes(ax, theme, family)
        step = max(1, len(days) // 10)
        ax.set_xticks(days[::step], [d.strftime("%d %b") for d in days[::step]])
        ax.legend(frameon=False, labelcolor=theme.muted, prop={"family": family, "size": 8}, loc="upper left",
                  ncols=2 if len(series) > 5 else 1)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"arrival rate chart failed: {exc}") from exc
