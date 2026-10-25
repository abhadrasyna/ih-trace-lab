"""Pie / donut chart: slices from the theme palette, every slice labelled with value and share."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

from src.lib.charts.axes import format_count, format_pct
from src.lib.charts.errors import ChartError, require_series
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family

logger = logging.getLogger(__name__)

OTHER_LABEL = "other"
DONUT_WIDTH = 0.42
# Pie above, legend below: long labels never clip at the figure edge.
PIE_AXES = [0.2, 0.36, 0.6, 0.52]


def merge_small_slices(
    labels: Sequence[str], values: Sequence[float], max_slices: int
) -> tuple[list[str], list[float]]:
    """Largest slices first; anything beyond ``max_slices - 1`` is summed into one ``other`` slice."""
    pairs = sorted(zip((str(label) for label in labels), values, strict=True), key=lambda p: -p[1])
    if len(pairs) <= max_slices:
        return [p[0] for p in pairs], [p[1] for p in pairs]
    kept, rest = pairs[: max_slices - 1], pairs[max_slices - 1 :]
    return [p[0] for p in kept] + [OTHER_LABEL], [p[1] for p in kept] + [sum(p[1] for p in rest)]


def require_pie_input(labels: Sequence[str], values: Sequence[float], max_slices: int, theme: ChartTheme) -> None:
    require_series(labels, values)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ChartError("pie values must be finite, non-negative numbers")
    if sum(values) <= 0:
        raise ChartError("pie values must have a positive total")
    if not 2 <= max_slices <= max(len(theme.series), 2):
        raise ChartError(f"max_slices must be between 2 and {len(theme.series)} (the palette size)")


def slice_label(name: str, value: float, total: float) -> str:
    return f"{name}: {format_count(value)} ({format_pct(100 * value / total)})"


def render_pie(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str,
    subtitle: str = "",
    donut: bool = True,
    max_slices: int = 6,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders a pie (or donut) to PNG bytes; raises ``ChartError`` on bad input or any drawing failure.

    Slices beyond ``max_slices - 1`` merge into ``other`` (drawn in the muted colour). A legend below the pie lists every
    slice with its value and share of the total.
    """
    require_pie_input(labels, values, max_slices, theme)
    try:
        names, vals = merge_small_slices(labels, values, max_slices)
        total = float(sum(vals))
        colours = [theme.muted if n == OTHER_LABEL else theme.series[i % len(theme.series)]
                   for i, n in enumerate(names)]
        family = chart_font_family()
        fig = new_figure(theme)
        ax = fig.add_subplot(111)
        ax.set_position(PIE_AXES)
        wedges, _ = ax.pie(vals, colors=colours, startangle=90, counterclock=False,
               wedgeprops={"width": DONUT_WIDTH if donut else 1.0, "edgecolor": theme.bg, "linewidth": 1.5})
        ax.set_aspect("equal")
        fig.legend(
            wedges, [slice_label(n, v, total) for n, v in zip(names, vals, strict=True)],
            loc="lower center", bbox_to_anchor=(0.5, 0.02), frameon=False, labelcolor=theme.ink,
            prop={"family": family, "size": 9.5},
        )
        if donut:
            ax.text(0, 0, format_count(total), ha="center", va="center", color=theme.ink, fontsize=15,
                    fontweight="bold", family=family)
        fig.text(0.13, 0.95, title, color=theme.ink, fontsize=13, fontweight="bold", family=family)
        if subtitle:
            fig.text(0.13, 0.915, subtitle, color=theme.muted, fontsize=9.5, family=family)
        png = render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"pie render failed: {exc}") from exc
    logger.info("pie rendered %d bytes", len(png))
    return png
