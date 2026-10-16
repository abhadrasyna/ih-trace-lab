"""Bar chart: neutral bars, sign colours only when the series has negative values."""

from __future__ import annotations

import logging
from typing import Sequence

from src.lib.charts.axes import style_axes
from src.lib.charts.errors import ChartError, require_series
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family

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
        ax.bar(range(len(values)), values, color=bar_colors(values, theme), width=0.65)
        ax.set_xticks(range(len(labels)), [str(label) for label in labels])
        ax.axhline(0, color=theme.muted, lw=0.8)
        style_axes(ax, theme, family)
        fig.text(0.13, 0.95, title, color=theme.ink, fontsize=13, fontweight="bold", family=family)
        if subtitle:
            fig.text(0.13, 0.915, subtitle, color=theme.muted, fontsize=9.5, family=family)
        png = render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"bar render failed: {exc}") from exc
    logger.info("bar rendered %d bytes", len(png))
    return png
