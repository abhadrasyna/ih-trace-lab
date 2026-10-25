"""Stacked bar chart: one stack per label, segments labelled directly, palette from the theme."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence

from matplotlib.axes import Axes

from src.lib.charts.axes import (
    format_count,
    format_pct,
    format_share_axis,
    format_value_axis,
    style_axes,
)
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import BASE_HEIGHT, TWO_ROW_HEIGHT, new_figure, render_png
from src.lib.charts.header import UNDER_TITLE_AXES_TOP, UNDER_TITLE_SHIFT, HeaderCell, draw_header, require_single_row
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.charts.title import draw_title

logger = logging.getLogger(__name__)

COLOUR_TOKENS = ("ink", "muted", "faint", "green", "red", "amber")
# A segment narrower than this share of the longest stack is too small to carry its own label.
MIN_LABEL_SHARE = 0.05
# A horizontal single-series bar must be this share of the longest to hold its "count (share)" text inside.
MIN_INSIDE_LABEL_SHARE_HORIZONTAL = 0.25
# A single-series bar shorter than this share of the longest is drawn at this height so it stays visible.
MIN_BAR_SHARE = 0.02
LEGEND_OPTIONS = ("auto", "above", False)
SHARE_TOTAL = 100.0
LEGEND_TOP_MARGIN = 0.82  # axes top when the legend sits above the plot, below the title block


def require_legend_option(legend: object) -> None:
    """Rejects anything but ``"auto"`` (legend inside the plot for several series), ``"above"`` or ``False``."""
    if legend != "auto" and legend != "above" and legend is not False:
        raise ChartError(f"legend must be one of {LEGEND_OPTIONS}, got {legend!r}")


def normalized_series(series: Mapping[str, Sequence[float]], stack_totals: Sequence[float]) -> dict[str, list[float]]:
    """Scales every stack to ``SHARE_TOTAL``; a stack whose total is zero stays all zeros (drawn empty)."""
    return {
        name: [SHARE_TOTAL * v / t if t else 0.0 for v, t in zip(values, stack_totals, strict=True)]
        for name, values in series.items()
    }


def require_bar_colours(bar_colours: Sequence[str] | None, labels: Sequence[str], n_series: int) -> None:
    """Per-bar colours apply to single-series charts only and need one colour per label."""
    if bar_colours is None:
        return
    if n_series != 1:
        raise ChartError("bar_colours needs exactly one series")
    if len(bar_colours) != len(labels):
        raise ChartError(f"bar_colours has {len(bar_colours)} colours for {len(labels)} labels")


def drawn_value(value: float, longest: float, single_series: bool) -> float:
    """Height actually drawn: a single-series bar under ``MIN_BAR_SHARE`` of the longest is lifted to it."""
    if single_series and 0 < value < MIN_BAR_SHARE * longest:
        return MIN_BAR_SHARE * longest
    return value


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
    bar_colours: Sequence[str] | None = None,
    total: float | None = None,
    normalize: bool = False,
    legend: bool | str = "auto",
    header: Sequence[HeaderCell] | None = None,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders stacked bars to PNG bytes; raises ``ChartError`` on bad input or any drawing failure.

    ``series`` maps a series name to one value per label. ``total`` adds each segment's share to its label.
    ``normalize`` scales each stack to 100% (axis ``0%``..``100%``; labels show the count and its share of that
    stack; a zero-total stack is drawn empty). ``legend="auto"`` draws a legend inside the plot only for more than
    one series; ``"above"`` puts it above the plot, outside the bars; ``False`` never draws one. ``bar_colours``
    (single series only) gives each bar its own colour. In a single-series chart a bar under ``MIN_LABEL_SHARE``
    of the longest (``MIN_INSIDE_LABEL_SHARE_HORIZONTAL`` when horizontal) is labelled above the bar, and one under ``MIN_BAR_SHARE`` is also lifted to that minimum height.
    ``header`` (1..6 cells) draws a stat header under the title block; it cannot be combined with ``legend="above"``.
    """
    require_stacked_input(labels, series)
    require_legend_option(legend)
    if header:
        require_single_row(header)
    if header and legend == "above":
        raise ChartError('header and legend="above" both claim the space under the title')
    require_bar_colours(bar_colours, labels, len(series))
    names = list(series)
    single = len(names) == 1
    try:
        colour_list = series_colours(names, colours, theme)
        family = chart_font_family()
        fig = new_figure(theme, TWO_ROW_HEIGHT if header else BASE_HEIGHT)
        if header:
            fig.subplots_adjust(top=UNDER_TITLE_AXES_TOP)
        ax = fig.add_subplot(111)
        positions = list(range(len(labels)))
        stack_totals = [sum(series[n][i] for n in names) for i in positions]
        plotted = normalized_series(series, stack_totals) if normalize else series
        longest = max(sum(plotted[n][i] for n in names) for i in positions) or 1.0
        base = [0.0] * len(labels)
        for name, colour in zip(names, colour_list, strict=True):
            values = list(plotted[name])
            drawn = [drawn_value(v, longest, single) for v in values]
            bar_colour = list(bar_colours) if bar_colours is not None else colour
            if horizontal:
                ax.barh(positions, drawn, left=base, color=bar_colour, height=0.65, label=name)
            else:
                ax.bar(positions, drawn, bottom=base, color=bar_colour, width=0.65, label=name)
            for i, v in enumerate(values):
                if v <= 0:
                    continue
                text = segment_label(series[name][i], stack_totals[i] if normalize else total)
                if v / longest < (MIN_INSIDE_LABEL_SHARE_HORIZONTAL if single and horizontal else MIN_LABEL_SHARE):
                    if single:
                        _label_above(ax, i, drawn[i], text, horizontal, theme, family)
                    continue
                mid = base[i] + v / 2
                x, y = (mid, i) if horizontal else (i, mid)
                ax.text(x, y, text, ha="center", va="center", color=theme.bg,
                        fontsize=8.5, fontweight="bold", family=family)
            base = [b + v for b, v in zip(base, drawn, strict=True)]
        ticks = [str(label) for label in labels]
        if horizontal:
            ax.set_yticks(positions, ticks)
            ax.invert_yaxis()
        else:
            ax.set_xticks(positions, ticks)
        style_axes(ax, theme, family)
        format_value_axis(ax, horizontal)
        if horizontal:
            ax.yaxis.grid(False)
            ax.xaxis.grid(True, color=theme.faint, lw=0.6)
        if single:
            if horizontal:
                ax.margins(x=0.12)
            else:
                ax.margins(y=0.12)
        if normalize:
            format_share_axis(ax, horizontal)
        if legend == "above":
            fig.subplots_adjust(top=LEGEND_TOP_MARGIN)
            key = ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=len(names), frameon=False,
                            labelcolor=theme.muted, prop={"family": family, "size": 8.5})
            key.set_zorder(10)
        elif legend == "auto" and not single:
            key = ax.legend(frameon=False, labelcolor=theme.muted, prop={"family": family, "size": 8.5})
            key.set_zorder(10)
        draw_title(fig, title, subtitle, theme, family)
        if header:
            draw_header(fig, header, theme, family, y_shift=UNDER_TITLE_SHIFT)
        png = render_png(fig, theme)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"stacked bar render failed: {exc}") from exc
    logger.info("stacked bar rendered %d bytes", len(png))
    return png


def _label_above(ax: Axes, index: int, end: float, text: str, horizontal: bool, theme: ChartTheme,
                 family: str) -> None:
    """Writes ``text`` just past the end of a bar too small to hold its own label."""
    xy, offset, ha, va = ((end, index), (4, 0), "left", "center") if horizontal else (
        (index, end), (0, 3), "center", "bottom")
    ax.annotate(text, xy=xy, xytext=offset, textcoords="offset points", ha=ha, va=va, color=theme.ink,
                fontsize=8.5, fontweight="bold", family=family)
