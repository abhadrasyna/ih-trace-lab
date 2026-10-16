import re
from pathlib import Path

import pytest

from src.lib.charts import header
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import BASE_HEIGHT, TWO_ROW_HEIGHT, new_figure, render_png
from src.lib.charts.header import HeaderCell, Tone, draw_header, header_figure_height, pack_cells, tone_colour
from src.lib.charts.theme import DARK, chart_font_family


def _cells(n: int, value: str = "1.2M") -> list[HeaderCell]:
    return [HeaderCell(f"Metric {i}", value) for i in range(n)]


def test_packing_one_row_vs_two_rows():
    assert len(pack_cells(_cells(3))) == 1
    rows = pack_cells(_cells(6, value="1,234,567,890 sessions"))
    assert [len(r) for r in rows] == [3, 3]
    assert [c for r in rows for c in r] == _cells(6, value="1,234,567,890 sessions")


def test_single_oversized_cell_stays_one_row():
    cell = HeaderCell("Label", "x" * 200)
    rows = pack_cells([cell])
    assert rows == [[cell]]
    fig = new_figure(DARK, header_figure_height(rows))
    assert draw_header(fig, [cell], DARK, chart_font_family()) == rows


def test_uneven_cells_do_not_overlap():
    row = [HeaderCell("A", "1"), HeaderCell("B", "x" * 20), HeaderCell("C", "2")]
    xs = header.cell_x_positions(row)
    for i in range(2):
        assert (xs[i + 1] - xs[i]) * header.BASE_WIDTH >= header.cell_width_in(row[i])


def test_packing_rejects_bad_cell_counts():
    for n in (0, 7):
        with pytest.raises(ChartError):
            pack_cells(_cells(n))


def test_tone_uses_theme_colours():
    assert tone_colour(Tone.POSITIVE, DARK) == DARK.green
    assert tone_colour(Tone.NEGATIVE, DARK) == DARK.red
    assert tone_colour(Tone.NEUTRAL, DARK) == DARK.ink
    assert tone_colour(Tone.MUTED, DARK) == DARK.muted
    assert not re.search(r"#[0-9a-fA-F]{6}", Path(header.__file__).read_text())


def test_draw_header_renders_rows_and_height():
    cells = _cells(6, value="1,234,567,890 sessions")
    rows = pack_cells(cells)
    fig = new_figure(DARK, header_figure_height(rows))
    assert fig.get_size_inches()[1] == pytest.approx(TWO_ROW_HEIGHT)
    assert header_figure_height(pack_cells(_cells(2))) == BASE_HEIGHT
    assert draw_header(fig, cells, DARK, chart_font_family()) == rows
    assert len(fig.texts) == 12
    assert render_png(fig, DARK).startswith(b"\x89PNG")
