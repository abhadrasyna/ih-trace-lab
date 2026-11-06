"""Bar chart: soft rounded bars, neutral unless the series has negative values (then green/red by sign)."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from src.lib.charts.axes import format_value_axis, style_axes
from src.lib.charts.errors import ChartError, require_series
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.shapes import add_bars
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.charts.title import draw_title

logger = logging.getLogger(__name__)


def bar_colors(values: Sequence[float], theme: ChartTheme) -> list[str]:
    """Neutral ``ink`` for an unsigned series; green/red by sign when any value is negative."""
    if all(v >= 0 for v in values):
        return [theme.ink] * len(values)
    return [theme.green if v >= 0 else theme.red for v in values]


def render_bar(
    labels: Sequence[str], values: Sequence[float], *, title: str, subtitle: str = "", theme: ChartTheme = DARK
) -> bytes:
    """Renders the bars to PNG bytes; raises ``ChartError`` on bad input or any drawing failure."""
    require_series(labels, values)
    try:
        family = chart_font_family()
        fig = new_figure(theme)
        ax = fig.add_subplot(111)
        top = max(max(values), 0.0)
        bottom = min(min(values), 0.0)
        pad = (top - bottom) * 0.12 or 1.0
        add_bars(ax, range(len(values)), values, bar_colors(values, theme), theme.corner_radius_in)
        ax.set_xlim(-0.6, len(values) - 0.4)
        ax.set_ylim(bottom - (pad if bottom < 0 else 0), top + pad)
        ax.set_xticks(range(len(labels)), [str(label) for label in labels])
        ax.axhline(0, color=theme.muted, lw=0.8)
        style_axes(ax, theme, family)
        format_value_axis(ax)
        draw_title(fig, title, subtitle, theme, family)
        png = render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"bar render failed: {exc}") from exc
    logger.info("bar rendered %d bytes", len(png))
    return png
