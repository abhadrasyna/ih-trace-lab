"""Offline tests for scripts/lib/lightstep_stitch.py and the part-file reader in lightstep_csv.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import lightstep_csv as lc
from scripts.lib import lightstep_stitch as ls

COLUMNS = ("fcId", "code", "min", "max", "avg", "sum", "value")


def _series(fc: str, code: str, points: list[list[float]]) -> dict[str, object]:
    return {"group-labels": [f"fcId={fc}", f"code={code}"], "points": points}


def _one_shot_rows(series: list[dict[str, object]]) -> list[list[str]]:
    return lc.build_rows(series, COLUMNS)


def test_stitch_series_equals_one_shot() -> None:
    whole = [_series("a", "200", [[1, 4], [2, 2], [3, 6], [4, 8]]), _series("b", "500", [[3, 5], [4, 1]])]
    part1 = [_series("a", "200", [[1, 4], [2, 2]])]
    part2 = [_series("b", "500", [[3, 5], [4, 1]]), _series("a", "200", [[3, 6], [4, 8]])]
    stitched = ls.stitch_series([part1, part2])
    assert {tuple(s["group-labels"]): s["points"] for s in stitched} == {  # type: ignore[arg-type]
        tuple(s["group-labels"]): s["points"] for s in whole  # type: ignore[arg-type]
    }
    assert sorted(_one_shot_rows(stitched)[1:]) == sorted(_one_shot_rows(whole)[1:])


def test_stitch_series_drops_duplicate_timestamps() -> None:
    stitched = ls.stitch_series([[_series("a", "200", [[1, 4], [2, 2]])], [_series("a", "200", [[2, 2], [3, 6]])]])
    assert stitched[0]["points"] == [[1, 4], [2, 2], [3, 6]]


def test_stitch_rows_recomputes_stats_across_parts() -> None:
    whole = [_series("a", "200", [[1, 4], [2, 2], [3, 6], [4, 8], [5, 10]])]
    part1 = _one_shot_rows([_series("a", "200", [[1, 4], [2, 2]])])
    part2 = _one_shot_rows([_series("a", "200", [[3, 6], [4, 8], [5, 10]])])
    assert ls.stitch_rows([part1, part2]) == _one_shot_rows(whole)


def test_stitch_rows_unions_label_sets_and_keeps_first_seen_order() -> None:
    part1 = _one_shot_rows([_series("a", "200", [[1, 1]])])
    part2 = _one_shot_rows([_series("b", "200", [[1, 2]]), _series("a", "200", [[2, 3]])])
    merged = ls.stitch_rows([part1, part2])
    assert [row[:2] for row in merged[1:]] == [["a", "200"], ["b", "200"]]
    assert merged[1][2:6] == ["1", "3", "2", "4"]


def test_stitch_rows_zero_average_part_uses_modal_count() -> None:
    part1 = _one_shot_rows([_series("a", "200", [[1, 0], [2, 0]]), _series("b", "200", [[1, 2], [2, 4]])])
    part2 = _one_shot_rows([_series("a", "200", [[3, 6], [4, 6]])])
    merged = ls.stitch_rows([part1, part2])
    assert merged[1][2:6] == ["0", "6", "3", "12"]


def test_stitch_rows_empty_stats_stay_empty() -> None:
    part = _one_shot_rows([_series("a", "200", [[1, None]])])  # type: ignore[list-item]
    assert ls.stitch_rows([part, part])[1][2:7] == ["", "", "", "", ""]


def test_stitch_rows_rejects_bad_input() -> None:
    good = _one_shot_rows([_series("a", "200", [[1, 1]])])
    with pytest.raises(ls.StitchError):
        ls.stitch_rows([])
    with pytest.raises(ls.StitchError):
        ls.stitch_rows([good, [["fcId", "min", "max", "avg", "sum", "value"]]])
    with pytest.raises(ls.StitchError):
        ls.stitch_rows([[["fcId", "foo"]]])


def test_read_rows_round_trips_written_file(tmp_path: Path) -> None:
    rows = _one_shot_rows([_series("a", 'x,"y"', [[1, 1]])])
    target = tmp_path / "part.csv"
    lc.write_rows(target, rows)
    assert lc.read_rows(target) == rows


def test_read_rows_rejects_missing_bom_empty_and_ragged(tmp_path: Path) -> None:
    plain = tmp_path / "plain.csv"
    plain.write_text('"a","b"\n"1","2"', encoding="utf-8")
    with pytest.raises(ValueError, match="BOM"):
        lc.read_rows(plain)
    empty = tmp_path / "empty.csv"
    empty.write_text("\ufeff", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        lc.read_rows(empty)
    ragged = tmp_path / "ragged.csv"
    ragged.write_text('\ufeff"a","b"\n"1"', encoding="utf-8")
    with pytest.raises(ValueError, match="row 2"):
        lc.read_rows(ragged)
