"""Stacked bar chart: one stack per label, segments labelled directly, palette from the theme."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence

from src.lib.charts.axes import format_count, format_pct, style_axes
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family

logger = logging.getLogger(__name__)

COLOUR_TOKENS = ("ink", "muted", "faint", "green", "red")
# A segment narrower than this share of the longest stack is too small to carry its own label.
MIN_LABEL_SHARE = 0.05


def require_stacked_input(labels: Sequence[str], series: Mapping[str, Sequence[float]]) -> None:
    """Rejects empty input, unequal lengths, and negative or non-finite values before any drawing."""
    if len(labels) == 0 or len(series) == 0:
        raise ChartError("chart input must not be empty")
    for name, values in series.items():
        if len(values) != len(labels):
            raise ChartError(f"series {name!r} has {len(values)} values for {len(labels)} labels")
        if any(not _is_valid_value(v) for v in values):
            raise ChartError(f"series {name!r} has a negative, non-finite or non-numeric value")


def _is_valid_value(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value >= 0


def series_colours(names: Sequence[str], colours: Mapping[str, str] | None, theme: ChartTheme) -> list[str]:
    """Colour per series: the ``colours`` token (e.g. ``green``) if given, else the theme palette in order."""
    colours = colours or {}
    if not theme.series and any(n not in colours for n in names):
        raise ChartError("theme has no series palette")
    out: list[str] = []
    for i, name in enumerate(names):
        if name in colours:
            token = colours[name]
            if token not in COLOUR_TOKENS:
                raise ChartError(f"unknown colour token {token!r} for series {name!r}; use one of {COLOUR_TOKENS}")
            out.append(getattr(theme, token))
        else:
            out.append(theme.series[i % len(theme.series)])
    return out


def segment_label(value: float, total: float | None) -> str:
    """Value, with its share of ``total`` when a positive total is given."""
    text = format_count(value)
    return f"{text} ({format_pct(100 * value / total)})" if total else text


def render_stacked_bar(
    labels: Sequence[str],
    series: Mapping[str, Sequence[float]],
    *,
    title: str,
    subtitle: str = "",
    horizontal: bool = False,
    colours: Mapping[str, str] | None = None,
    total: float | None = None,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders stacked bars to PNG bytes; raises ``ChartError`` on bad input or any drawing failure.

    ``series`` maps a series name to one value per label. ``total`` adds each segment's share to its label.
    A legend appears only when some segment is too small to be labelled directly.
    """
    require_stacked_input(labels, series)
    names = list(series)
    try:
        colour_list = series_colours(names, colours, theme)
        family = chart_font_family()
        fig = new_figure(theme)
        ax = fig.add_subplot(111)
        positions = list(range(len(labels)))
        stack_totals = [sum(series[n][i] for n in names) for i in positions]
        longest = max(stack_totals) or 1.0
        base = [0.0] * len(labels)
        skipped = False
        for name, colour in zip(names, colour_list, strict=True):
            values = list(series[name])
            if horizontal:
                ax.barh(positions, values, left=base, color=colour, height=0.65, label=name)
            else:
                ax.bar(positions, values, bottom=base, color=colour, width=0.65, label=name)
            for i, v in enumerate(values):
                if v <= 0:
                    continue
                if v / longest < MIN_LABEL_SHARE:
                    skipped = True
                    continue
                mid = base[i] + v / 2
                x, y = (mid, i) if horizontal else (i, mid)
                ax.text(x, y, segment_label(v, total), ha="center", va="center", color=theme.bg,
                        fontsize=8.5, fontweight="bold", family=family)
            base = [b + v for b, v in zip(base, values, strict=True)]
        ticks = [str(label) for label in labels]
        if horizontal:
            ax.set_yticks(positions, ticks)
            ax.invert_yaxis()
        else:
            ax.set_xticks(positions, ticks)
        style_axes(ax, theme, family)
        if horizontal:
            ax.yaxis.grid(False)
            ax.xaxis.grid(True, color=theme.faint, lw=0.6)
        if skipped:
            legend = ax.legend(frameon=False, labelcolor=theme.muted, prop={"family": family, "size": 8.5})
            legend.set_zorder(10)
        fig.text(0.13, 0.95, title, color=theme.ink, fontsize=13, fontweight="bold", family=family)
        if subtitle:
            fig.text(0.13, 0.915, subtitle, color=theme.muted, fontsize=9.5, family=family)
        png = render_png(fig, theme)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"stacked bar render failed: {exc}") from exc
    logger.info("stacked bar rendered %d bytes", len(png))
    return png
