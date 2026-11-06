"""Rate bars: one labelled row per category with a track, for rates, shares and rankings.

Each row reads "label above the bar, bar on a faint track, value at the end". Use it when the question is "how big is
each one": the track makes "65 of 100" visible without an axis.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from src.lib.charts.canvas import (
    CHAR_WIDTH_IN, LEFT, MAX_ROWS, PLOT_BOTTOM, PLOT_TOP, RIGHT, finish, frame, new_canvas, require_values,
)
from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK, ChartTheme, resolve_colour

logger = logging.getLogger(__name__)

BAR_HEIGHT_IN = 0.3
VALUE_GUTTER_IN = 0.85
MIN_BAR_IN = 0.12
# Above this many rows a label cannot sit over its bar, so labels move to the left of the bars.
MAX_STACKED_ROWS = 4


@dataclass(frozen=True)
class RateRow:
    label: str
    value: float
    text: str
    colour: str = "red"


def render_rate_bars(
    rows: Sequence[RateRow],
    *,
    title: str,
    subtitle: str = "",
    footer: str = "",
    vmax: float = 100.0,
    track: bool = True,
    inline_labels: bool = False,
    theme: ChartTheme = DARK,
) -> bytes:
    """Renders the rows to PNG bytes; ``inline_labels`` puts short labels left of the bars (rankings).

    ``vmax`` is the value a full track stands for (100 for a rate). Raises ``ChartError`` on bad input.
    """
    if not 1 <= len(rows) <= MAX_ROWS:
        raise ChartError(f"rate bars need 1 to {MAX_ROWS} rows, got {len(rows)}")
    if vmax <= 0:
        raise ChartError("vmax must be positive")
    values = [r.value for r in rows]
    require_values(values)
    if any(v < 0 or v > vmax for v in values):
        raise ChartError(f"rate bar values must be within 0..{vmax}")
    try:
        c = new_canvas(theme)
        frame(c, title, subtitle, footer)
        inline_labels = inline_labels or len(rows) > MAX_STACKED_ROWS
        gutter = max(len(r.label) for r in rows) * CHAR_WIDTH_IN + 0.3 if inline_labels else 0.0
        x0 = LEFT + gutter
        value_gutter = max(VALUE_GUTTER_IN, max(len(r.text) for r in rows) * CHAR_WIDTH_IN * 1.15 + 0.2)
        span = RIGHT - x0 - value_gutter
        pitch = (PLOT_BOTTOM - PLOT_TOP) / len(rows)
        height = min(BAR_HEIGHT_IN, pitch * 0.6)
        for i, row in enumerate(rows):
            y = PLOT_TOP + i * pitch
            by = y if inline_labels else y + 0.3
            colour = resolve_colour(row.colour, theme)
            if inline_labels:
                c.text(LEFT, by + height / 2, row.label)
            else:
                c.text(LEFT, y + 0.1, row.label, colour=theme.muted)
            if track:
                c.bar(x0, by, span, height, theme.faint, z=1)
            width = max(row.value / vmax * span, MIN_BAR_IN)
            c.bar(x0, by, width, height, colour)
            end = x0 + (span if track else width) + 0.12
            c.text(end, by + height / 2, row.text, size=12, weight="bold")
        png = finish(c)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"rate bars render failed: {exc}") from exc
    logger.info("rate_bars rendered %d bytes", len(png))
    return png
