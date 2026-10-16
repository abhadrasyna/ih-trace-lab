import pytest

from src.lib.charts.bar import bar_colors, render_bar
from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK


def test_bar_returns_png():
    assert render_bar(["a", "b", "c"], [3, -1, 2], title="t").startswith(b"\x89PNG")


def test_unsigned_bars_are_neutral_and_signed_use_sign_colours():
    assert bar_colors([1, 2], DARK) == [DARK.ink, DARK.ink]
    assert bar_colors([1, -2], DARK) == [DARK.green, DARK.red]


def test_mismatched_lengths_raise_chart_error():
    with pytest.raises(ChartError):
        render_bar(["a"], [1, 2], title="t")


def test_empty_input_raises_chart_error():
    with pytest.raises(ChartError):
        render_bar([], [], title="t")
