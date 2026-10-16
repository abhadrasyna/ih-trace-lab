from src.lib.charts.fig import BASE_HEIGHT, TWO_ROW_HEIGHT, new_figure, render_png
from src.lib.charts.theme import DARK


def test_render_png_magic_bytes():
    fig = new_figure(DARK)
    fig.add_subplot(111).plot([1, 2, 3])
    assert render_png(fig, DARK).startswith(b"\x89PNG")


def test_new_figure_sizes_and_margins():
    plain, tall = new_figure(DARK), new_figure(DARK, TWO_ROW_HEIGHT)
    assert plain.get_size_inches()[1] == BASE_HEIGHT
    assert tall.get_size_inches()[1] == TWO_ROW_HEIGHT
    assert tall.subplotpars.top < plain.subplotpars.top
