import pytest

from src.lib.charts.axes import format_count, format_pct, nice_ticks, padded_range, style_axes
from src.lib.charts.fig import new_figure
from src.lib.charts.theme import DARK


def test_format_count_abbreviates():
    assert format_count(1500) == "1.5k"
    assert format_count(2_000_000) == "2M"
    assert format_count(-1500) == "-1.5k"
    assert format_count(0) == "0"
    assert format_count(999) == "999"


def test_format_pct():
    assert format_pct(12.5) == "12.5%"
    assert format_pct(3) == "3%"


def test_padded_range_flat_and_empty():
    assert padded_range([5, 5]) == (4.0, 6.0)
    with pytest.raises(ValueError):
        padded_range([])


def test_nice_ticks():
    assert nice_ticks(0, 100) == [0, 50, 100]
    ticks = nice_ticks(0, 97)
    assert ticks[0] <= 0 and ticks[-1] >= 97
    assert nice_ticks(3, 3) == [3]
    with pytest.raises(ValueError):
        nice_ticks(0, 1, target=1)


def test_style_axes_quiet_chrome():
    ax = new_figure(DARK).add_subplot(111)
    style_axes(ax, DARK, "DejaVu Sans")
    assert not ax.spines["top"].get_visible() and not ax.spines["right"].get_visible()
    assert ax.get_axisbelow() is True


def test_format_rounding_edges():
    assert format_count(999_950) == "1M"
    assert format_count(999_960_000) == "1B"
    assert format_count(-0.04) == "0"
    assert format_pct(-0.04) == "0%"
    assert format_pct(-2.5) == "-2.5%"
