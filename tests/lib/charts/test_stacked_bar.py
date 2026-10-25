import re

import pytest
from matplotlib.axes import Axes

from src.lib.charts import stacked_bar
from src.lib.charts.errors import ChartError
from src.lib.charts.stacked_bar import (
    MIN_BAR_SHARE,
    drawn_value,
    normalized_series,
    render_stacked_bar,
    segment_label,
    series_colours,
)
from src.lib.charts.theme import DARK

SERIES = {"success": [90, 40], "failed": [10, 2]}


@pytest.mark.parametrize("horizontal", [False, True])
def test_renders_png_bytes_for_vertical_and_horizontal(horizontal):
    png = render_stacked_bar(["widevine", "fairplay"], SERIES, title="t", subtitle="s", horizontal=horizontal, total=142)
    assert png.startswith(b"\x89PNG")


def test_tiny_segment_still_renders_with_legend():
    assert render_stacked_bar(["a"], {"big": [1000], "tiny": [1]}, title="t").startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "labels,series",
    [
        ([], SERIES),
        (["a", "b"], {}),
        (["a", "b"], {"x": [1]}),
        (["a", "b"], {"x": [1, -1]}),
        (["a", "b"], {"x": [1, float("nan")]}),
        (["a", "b"], {"x": [1, float("inf")]}),
        (["a", "b"], {"x": [1, None]}),
        (["a", "b"], {"x": [1, "2"]}),
    ],
)
def test_unequal_series_lengths_and_negative_values_raise_chart_error(labels, series):
    with pytest.raises(ChartError):
        render_stacked_bar(labels, series, title="t")


def test_series_colours_come_from_theme_palette():
    assert series_colours(["a", "b", "c"], None, DARK) == list(DARK.series[:3])
    mapped = series_colours(["ok", "bad", "x"], {"ok": "green", "bad": "red"}, DARK)
    assert mapped == [DARK.green, DARK.red, DARK.series[2]]
    assert DARK.amber not in DARK.series and DARK.green not in DARK.series and DARK.red not in DARK.series
    with pytest.raises(ChartError):
        series_colours(["a"], {"a": "#ffffff"}, DARK)


def test_segment_label_adds_share_only_with_total():
    assert segment_label(1500, None) == "1.5k"
    assert segment_label(25, 100) == "25 (25%)"


@pytest.mark.parametrize("horizontal", [False, True])
def test_stacked_bar_axis_labels_abbreviated(monkeypatch, horizontal):
    figs = []
    real = stacked_bar.render_png
    monkeypatch.setattr(stacked_bar, "render_png", lambda fig, theme: figs.append(fig) or real(fig, theme))
    render_stacked_bar(["a", "b"], {"x": [1500, 2000], "y": [500, 1000]}, title="t", horizontal=horizontal)
    ax = figs[0].axes[0]
    labels = [t.get_text() for t in (ax.get_xticklabels() if horizontal else ax.get_yticklabels())]
    assert "2k" in labels and not any(re.fullmatch(r"\d{4,}", t) for t in labels)


def test_amber_colour_token_is_accepted():
    assert series_colours(["w"], {"w": "amber"}, DARK) == [DARK.amber]


def test_single_series_has_no_legend(monkeypatch):
    calls = []
    real = Axes.legend

    def spy(self, *args, **kwargs):
        calls.append(kwargs)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "legend", spy)
    assert render_stacked_bar(["a", "b"], {"vod": [10, 5]}, title="t").startswith(b"\x89PNG")
    assert calls == []
    render_stacked_bar(["a", "b"], {"vod": [10, 5], "linear": [2, 1]}, title="t")
    assert len(calls) == 1
    render_stacked_bar(["a", "b"], {"vod": [10, 5], "linear": [2, 1]}, title="t", legend=False)
    assert len(calls) == 1


def test_small_bar_label_above_bar(monkeypatch):
    labels = []
    real = Axes.annotate

    def spy(self, text, *args, **kwargs):
        labels.append(text)
        return real(self, text, *args, **kwargs)

    monkeypatch.setattr(Axes, "annotate", spy)
    png = render_stacked_bar(["big", "tiny"], {"vod": [1000, 3]}, title="t", bar_colours=["#111111", "#222222"])
    assert png.startswith(b"\x89PNG")
    assert labels == ["3"]
    assert drawn_value(3, 1000, single_series=True) == MIN_BAR_SHARE * 1000
    assert drawn_value(3, 1000, single_series=False) == 3
    assert drawn_value(0, 1000, single_series=True) == 0


@pytest.mark.parametrize("legend", ["below", None, 0, True])
def test_invalid_legend_option_raises_chart_error(legend):
    with pytest.raises(ChartError):
        render_stacked_bar(["a"], {"vod": [1]}, title="t", legend=legend)


def test_bar_colours_validated():
    with pytest.raises(ChartError):
        render_stacked_bar(["a", "b"], {"vod": [1, 2]}, title="t", bar_colours=["#111111"])
    with pytest.raises(ChartError):
        render_stacked_bar(["a"], {"x": [1], "y": [1]}, title="t", bar_colours=["#111111"])


def test_normalized_stacks_sum_to_100(monkeypatch):
    out = normalized_series({"ok": [30, 1], "bad": [10, 3]}, [40, 4])
    assert out == {"ok": [75.0, 25.0], "bad": [25.0, 75.0]}
    figs = []
    real = stacked_bar.render_png
    monkeypatch.setattr(stacked_bar, "render_png", lambda fig, theme: figs.append(fig) or real(fig, theme))
    png = render_stacked_bar(["a", "b"], {"ok": [30, 1], "bad": [10, 3]}, title="t", normalize=True)
    assert png.startswith(b"\x89PNG")
    ax = figs[0].axes[0]
    assert ax.get_ylim() == (0, 100)
    assert [t.get_text() for t in ax.get_yticklabels()][-1] == "100%"
    heights = [sum(p.get_height() for p in ax.patches if p.get_x() + p.get_width() / 2 == pos) for pos in (0, 1)]
    assert heights == pytest.approx([100.0, 100.0])


def test_zero_total_stack_handled():
    assert normalized_series({"ok": [0, 2], "bad": [0, 2]}, [0, 4]) == {"ok": [0.0, 50.0], "bad": [0.0, 50.0]}
    png = render_stacked_bar(["empty", "full"], {"ok": [0, 2], "bad": [0, 2]}, title="t", normalize=True)
    assert png.startswith(b"\x89PNG")
    assert render_stacked_bar(["empty"], {"ok": [0], "bad": [0]}, title="t", normalize=True).startswith(b"\x89PNG")


def test_legend_outside_plot_area(monkeypatch):
    calls = []
    real = Axes.legend

    def spy(self, *args, **kwargs):
        calls.append(kwargs)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "legend", spy)
    render_stacked_bar(["a"], {"ok": [3], "bad": [1]}, title="t", legend="above")
    assert len(calls) == 1
    x, y = calls[0]["bbox_to_anchor"]
    assert y >= 1.0 and calls[0]["ncol"] == 2


def test_header_draws_cells_and_rejects_above_legend():
    from src.lib.charts.header import HeaderCell, Tone

    cells = [HeaderCell("ERROR RATE", "42%", Tone.NEGATIVE)]
    assert render_stacked_bar(["a"], {"s": [3]}, title="t", header=cells).startswith(b"\x89PNG")
    with pytest.raises(ChartError):
        render_stacked_bar(["a"], {"s": [3]}, title="t", header=cells, legend="above")


def test_horizontal_single_series_moves_short_bar_labels_outside(monkeypatch):
    outside = []
    real = Axes.annotate

    def spy(self, text, *args, **kwargs):
        outside.append(text)
        return real(self, text, *args, **kwargs)

    monkeypatch.setattr(Axes, "annotate", spy)
    render_stacked_bar(["big", "mid", "small"], {"s": [100, 20, 3]}, title="t", horizontal=True)
    assert len(outside) == 2


def test_two_row_header_is_rejected():
    from src.lib.charts.header import HeaderCell

    cells = [HeaderCell(f"METRIC {i}", "1,234,567,890 sessions") for i in range(6)]
    with pytest.raises(ChartError):
        render_stacked_bar(["a"], {"s": [3]}, title="t", header=cells)
