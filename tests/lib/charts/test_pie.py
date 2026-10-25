import pytest

from src.lib.charts.errors import ChartError
from src.lib.charts.pie import OTHER_LABEL, merge_small_slices, render_pie, slice_label


def test_render_pie_returns_png_and_merges_small_slices_into_other():
    labels = ["a", "b", "c", "d", "e", "f", "g", "h"]
    values = [50, 40, 30, 20, 10, 5, 3, 2]
    names, vals = merge_small_slices(labels, values, 6)
    assert names == ["a", "b", "c", "d", "e", OTHER_LABEL]
    assert vals == [50, 40, 30, 20, 10, 10] and sum(vals) == sum(values)
    for donut in (True, False):
        assert render_pie(labels, values, title="t", subtitle="s", donut=donut).startswith(b"\x89PNG")


def test_few_slices_are_not_merged_and_zero_slices_render():
    assert merge_small_slices(["a", "b"], [1, 3], 6) == (["b", "a"], [3, 1])
    assert render_pie(["a", "b"], [5, 0], title="t").startswith(b"\x89PNG")
    assert slice_label("a", 1500, 3000) == "a: 1.5k (50%)"


@pytest.mark.parametrize(
    "labels,values,max_slices",
    [
        ([], [], 6),
        (["a", "b"], [1], 6),
        (["a", "b"], [1, -1], 5),
        (["a", "b"], [1, float("nan")], 5),
        (["a", "b"], [1, "2"], 5),
        (["a", "b"], [0, 0], 5),
        (["a", "b"], [1, 2], 1),
        (["a", "b"], [1, 2], 6),
    ],
)
def test_invalid_pie_input_raises_chart_error(labels, values, max_slices):
    with pytest.raises(ChartError):
        render_pie(labels, values, title="t", max_slices=max_slices)


def test_pie_default_max_slices_fits_palette():
    import inspect

    from src.lib.charts.theme import DARK

    assert inspect.signature(render_pie).parameters["max_slices"].default == len(DARK.series) == 5
    assert render_pie([str(i) for i in range(8)], list(range(1, 9)), title="t").startswith(b"\x89PNG")


def test_pie_rejects_max_slices_above_palette():
    with pytest.raises(ChartError):
        render_pie(["a", "b"], [1, 2], title="t", max_slices=6)
