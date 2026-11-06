"""Composition: one 100% bar split into directly labelled parts, for "what is the whole made of"."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from src.lib.charts.canvas import LEFT, RIGHT, finish, frame, new_canvas, on_colour, require_values
from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK, ChartTheme, resolve_colour

logger = logging.getLogger(__name__)

MAX_PARTS = 5
BAR_Y, BAR_H = 1.9, 0.7
SEGMENT_GAP_IN = 0.04
# A part narrower than this share of the whole cannot hold its percentage inside, so it sits above the bar.
MIN_INSIDE_SHARE = 0.12


@dataclass(frozen=True)
class Part:
    label: str
    value: float
    sub: str = ""  # count line under the label, e.g. "6,069 households"
    colour: str = "blue"


def render_composition(
    parts: Sequence[Part], *, title: str, subtitle: str = "", footer: str = "", theme: ChartTheme = DARK
) -> bytes:
    """Renders the parts as one bar of widths proportional to value; a zero total raises ``ChartError``."""
    if not 1 <= len(parts) <= MAX_PARTS:
        raise ChartError(f"a composition needs 1 to {MAX_PARTS} parts, got {len(parts)}")
    values = [p.value for p in parts]
    require_values(values)
    total = sum(values)
    if any(v < 0 for v in values) or total <= 0:
        raise ChartError("composition needs non-negative values with a positive total")
    try:
        c = new_canvas(theme)
        frame(c, title, subtitle, footer)
        span = RIGHT - LEFT
        x = LEFT
        for i, part in enumerate(parts):
            share = part.value / total
            width = max(share * span - SEGMENT_GAP_IN, 0.05)
            fill = resolve_colour(part.colour, theme)
            c.bar(x, BAR_Y, width, BAR_H, fill)
            pct = f"{share * 100:.0f}%"
            narrow = share < MIN_INSIDE_SHARE
            right_aligned = narrow and i == len(parts) - 1
            edge_x, ha = (x + width, "right") if right_aligned else (x, "left")
            if narrow:
                c.text(edge_x, BAR_Y - 0.2, pct, size=11, weight="bold", ha=ha)
            else:
                c.text(x + width / 2, BAR_Y + BAR_H / 2, pct, size=14, colour=on_colour(fill, theme), weight="bold",
                       ha="center")
            c.text(edge_x, BAR_Y + BAR_H + 0.3, part.label, weight="bold", ha=ha)
            if part.sub:
                c.text(edge_x, BAR_Y + BAR_H + 0.55, part.sub, size=8.5, colour=theme.muted, ha=ha)
            x += width + SEGMENT_GAP_IN
        png = finish(c)
    except ChartError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"composition render failed: {exc}") from exc
    logger.info("composition rendered %d bytes", len(png))
    return png
