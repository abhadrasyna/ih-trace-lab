"""Scratch-only helper — not for src/ or scripts/dev/ import. Graduate (with tests) before reuse there."""
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.dates as mdates  # noqa: E402

from src.lib.charts.axes import format_value_axis, padded_range, style_axes  # noqa: E402
from src.lib.charts.errors import ChartError, require_series  # noqa: E402
from src.lib.charts.fig import new_figure, render_png  # noqa: E402
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family  # noqa: E402
from src.lib.charts.title import draw_title  # noqa: E402


def render_line(
    xs: Sequence[float | datetime],
    ys: Sequence[float],
    *,
    title: str,
    subtitle: str = "",
    fill: bool = True,
    theme: ChartTheme = DARK,
) -> bytes:
    """Single neutral (unsigned) series as PNG bytes: ``series[0]`` line, optional light area fill.

    For counts, which carry no good/bad sign. ``xs`` may be datetimes (axis shows HH:MM). Zero baseline.
    """
    require_series(xs, ys)
    try:
        family = chart_font_family()
        fig = new_figure(theme)
        ax = fig.add_subplot(111)
        colour = theme.series[0]
        ax.plot(xs, ys, color=colour, lw=1.8, solid_capstyle="round")
        if fill:
            ax.fill_between(xs, 0, ys, color=colour, alpha=theme.fill_alpha_green, lw=0)
        ax.axhline(0, color=theme.muted, lw=0.8)
        ax.set_ylim(0, padded_range([*ys, 0.0])[1])
        style_axes(ax, theme, family)
        format_value_axis(ax)
        if isinstance(xs[0], datetime):
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            for label in ax.get_xticklabels():
                label.set_family(family)
        draw_title(fig, title, subtitle, theme, family)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"line render failed: {exc}") from exc
