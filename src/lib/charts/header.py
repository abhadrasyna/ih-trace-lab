"""Optional stat header: ``Tone``, ``HeaderCell``, pure cell packing and ``draw_header``.

Packing is pure (no matplotlib) so it can be tested without rendering. Colours come from ``ChartTheme`` only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from matplotlib.figure import Figure

from src.lib.charts.errors import ChartError
from src.lib.charts.fig import BASE_HEIGHT, BASE_WIDTH, TWO_ROW_HEIGHT
from src.lib.charts.theme import ChartTheme

MAX_CELLS = 6
# Width budget for one row, in figure inches, and the rough advance of one character per font size.
ROW_WIDTH_BUDGET_IN = BASE_WIDTH * 0.84
CELL_GAP_IN = 0.25
VALUE_FONT_SIZE = 12.0
LABEL_FONT_SIZE = 8.0
CHAR_WIDTH_PER_PT_IN = 0.0085
# Figure-fraction y of the label line for each row; the value sits just below it.
ROW_LABEL_Y_ONE = 0.965
ROW_LABEL_Y_TWO = (0.975, 0.895)
VALUE_Y_OFFSET = 0.035
LEFT_X = 0.13


class Tone(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MUTED = "muted"


@dataclass(frozen=True)
class HeaderCell:
    label: str
    value: str
    tone: Tone = Tone.NEUTRAL


def tone_colour(tone: Tone, theme: ChartTheme) -> str:
    """Maps a tone to a theme colour."""
    return {
        Tone.POSITIVE: theme.green,
        Tone.NEGATIVE: theme.red,
        Tone.NEUTRAL: theme.ink,
        Tone.MUTED: theme.muted,
    }[tone]


def cell_width_in(cell: HeaderCell) -> float:
    """Estimated width of one cell: the wider of its label and value text."""
    label_w = len(cell.label) * LABEL_FONT_SIZE * CHAR_WIDTH_PER_PT_IN
    value_w = len(cell.value) * VALUE_FONT_SIZE * CHAR_WIDTH_PER_PT_IN
    return max(label_w, value_w)


def row_width_in(cells: Sequence[HeaderCell]) -> float:
    if not cells:
        return 0.0
    return sum(cell_width_in(c) for c in cells) + CELL_GAP_IN * (len(cells) - 1)


def pack_cells(cells: Sequence[HeaderCell], budget_in: float = ROW_WIDTH_BUDGET_IN) -> list[list[HeaderCell]]:
    """Packs 1..MAX_CELLS cells into one row if they fit the width budget, else two balanced rows."""
    if not 1 <= len(cells) <= MAX_CELLS:
        raise ChartError(f"header needs 1 to {MAX_CELLS} cells, got {len(cells)}")
    if len(cells) == 1 or row_width_in(cells) <= budget_in:
        return [list(cells)]
    split = (len(cells) + 1) // 2
    return [list(cells[:split]), list(cells[split:])]


def header_figure_height(rows: Sequence[Sequence[HeaderCell]]) -> float:
    """Figure height to request from ``new_figure`` for the given packed rows."""
    return TWO_ROW_HEIGHT if len(rows) > 1 else BASE_HEIGHT


def cell_x_positions(row: Sequence[HeaderCell]) -> list[float]:
    """Left-aligned figure-fraction x per cell, placed by cumulative estimated width so no cell overlaps."""
    xs, cursor_in = [], 0.0
    for cell in row:
        xs.append(LEFT_X + cursor_in / BASE_WIDTH)
        cursor_in += cell_width_in(cell) + CELL_GAP_IN
    return xs


def draw_header(
    fig: Figure,
    cells: Sequence[HeaderCell],
    theme: ChartTheme,
    family: str,
    budget_in: float = ROW_WIDTH_BUDGET_IN,
) -> list[list[HeaderCell]]:
    """Draws the cells on ``fig`` and returns the packed rows; build ``fig`` with ``header_figure_height``."""
    rows = pack_cells(cells, budget_in)
    label_ys = (ROW_LABEL_Y_ONE,) if len(rows) == 1 else ROW_LABEL_Y_TWO
    for row, label_y in zip(rows, label_ys):
        for cell, x in zip(row, cell_x_positions(row)):
            fig.text(x, label_y, cell.label, color=theme.muted, fontsize=LABEL_FONT_SIZE, family=family, va="top")
            fig.text(
                x,
                label_y - VALUE_Y_OFFSET,
                cell.value,
                color=tone_colour(cell.tone, theme),
                fontsize=VALUE_FONT_SIZE,
                family=family,
                fontweight="bold",
                va="top",
            )
    return rows
