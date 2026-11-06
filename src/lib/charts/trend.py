"""Trend: one or more lines over a few periods, directly labelled, with an optional reference line."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.lib.charts.canvas import CHAR_WIDTH_IN, LEFT, RIGHT, finish, frame, new_canvas, require_values
from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK, ChartTheme, resolve_colour

logger = logging.getLogger(__name__)

MAX_SERIES = 3
Y_TOP, Y_BOTTOM = 1.5, 3.5
AXIS_GUTTER_IN = 0.55
LINE_WIDTH = 2.8
MARKER_AREA = 34
END_LABEL_GAP_IN = 0.2


@dataclass(frozen=True)
class TrendSeries:
    name: str
    values: Sequence[float]
    colour: str = "red"
    end_text: str = ""  # direct label at the line's end, e.g. "6001 sessions  130"
    label_points: Sequence[int] = ()  # indices that carry their own value label
    labels_below: bool = False


@dataclass(frozen=True)
class TrendReference:
    value: float
    label: str


def spread_labels(ys: dict[int, float], gap: float = END_LABEL_GAP_IN) -> dict[int, float]:
    """Nudges label positions (inches, y down) apart so no two end labels sit closer than ``gap``."""
    out: dict[int, float] = {}
    last = float("-inf")
    for key in sorted(ys, key=ys.get):
        last = out[key] = max(ys[key], last + gap)
    return out


def render_trend(
    labels: Sequence[str],
    series: Sequence[TrendSeries],
    *,
    title: str,
    subtitle: str = "",
    footer: str = "",
    lo: float,
    hi: float,
    ticks: Sequence[float],
    value_fmt: Callable[[float], str],
    tick_fmt: Callable[[float], str] | None = None,
    reference: TrendReference | None = None,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders straight-segment lines over ``labels`` (2+ periods); raises ``ChartError`` on bad input."""
    if len(labels) < 2:
        raise ChartError("a trend needs at least 2 periods")
    if not 1 <= len(series) <= MAX_SERIES:
        raise ChartError(f"a trend needs 1 to {MAX_SERIES} series, got {len(series)}")
    if hi <= lo:
        raise ChartError("hi must be greater than lo")
    for s in series:
        if len(s.values) != len(labels):
            raise ChartError(f"series {s.name!r} has {len(s.values)} values for {len(labels)} periods")
        require_values(list(s.values))
        if any(not lo <= v <= hi for v in s.values):
            raise ChartError(f"series {s.name!r} has a value outside {lo}..{hi}")
    try:
        c = new_canvas(theme)
        frame(c, title, subtitle, footer)
        end_pad = max((len(s.end_text) for s in series), default=0) * CHAR_WIDTH_IN + 0.35
        ref_pad = len(reference.label) * CHAR_WIDTH_IN * 0.9 + 0.2 if reference else 0.0
        x0, x1 = LEFT + AXIS_GUTTER_IN, RIGHT - max(end_pad, ref_pad, 0.3)
        px = lambda i: x0 + (x1 - x0) * i / (len(labels) - 1)  # noqa: E731
        py = lambda v: Y_BOTTOM + (Y_TOP - Y_BOTTOM) * (v - lo) / (hi - lo)  # noqa: E731
        for t in ticks:
            c.hline(x0 - 0.1, x1 + 0.1, py(t), theme.faint)
            c.text(LEFT, py(t), (tick_fmt or value_fmt)(t), size=8.5, colour=theme.muted)
        for i, lab in enumerate(labels):
            c.text(px(i), Y_BOTTOM + 0.35, lab, colour=theme.muted, ha="center")
        if reference:
            c.hline(x0 - 0.1, x1 + 0.1, py(reference.value), theme.muted, lw=1.2, z=2)
            c.text(x1 + 0.2, py(reference.value), reference.label, size=8.5, colour=theme.muted)
        end_y = spread_labels({i: py(s.values[-1]) for i, s in enumerate(series) if s.end_text})
        for n, s in enumerate(series):
            colour = resolve_colour(s.colour, theme)
            xs = [px(i) for i in range(len(labels))]
            ys = [py(v) for v in s.values]
            c.ax.plot(xs, ys, color=colour, lw=LINE_WIDTH, solid_capstyle="round", solid_joinstyle="round", zorder=3)
            c.ax.scatter(xs, ys, s=MARKER_AREA, color=colour, zorder=4, edgecolors=theme.bg, linewidths=1.5)
            if s.end_text:
                c.text(xs[-1] + 0.15, end_y[n], s.end_text, size=10, colour=colour, weight="bold")
            for i in s.label_points:
                dy = 0.26 if s.labels_below else -0.22
                c.text(xs[i], ys[i] + dy, value_fmt(s.values[i]), size=11, weight="bold", ha="center")
        png = finish(c)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"trend render failed: {exc}") from exc
    logger.info("trend rendered %d bytes", len(png))
    return png
