from src.lib.charts.fig import new_figure
from src.lib.charts.theme import DARK, chart_font_family
from src.lib.charts.title import draw_title


def test_draw_title_sizes_and_colours():
    fig = new_figure(DARK)
    draw_title(fig, "Title", "Sub", DARK, chart_font_family())
    title, sub = fig.texts
    assert (title.get_fontsize(), title.get_fontweight(), title.get_color()) == (16, "bold", DARK.ink)
    assert (sub.get_fontsize(), sub.get_color()) == (10, DARK.muted)


def test_draw_title_without_subtitle():
    fig = new_figure(DARK)
    draw_title(fig, "Title", "", DARK, chart_font_family())
    assert len(fig.texts) == 1


def test_long_title_is_truncated_inside_the_figure():
    fig = new_figure(DARK)
    draw_title(fig, "W" * 200, "", DARK, chart_font_family())
    text = fig.texts[0]
    assert text.get_text().endswith("…")
    assert text.get_window_extent(fig.canvas.get_renderer()).x1 <= fig.bbox.width


def test_short_title_is_untouched():
    fig = new_figure(DARK)
    draw_title(fig, "short", "", DARK, chart_font_family())
    assert fig.texts[0].get_text() == "short"
