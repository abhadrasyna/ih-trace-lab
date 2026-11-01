"""Tests for the pure sanity checks run before the part files are deleted."""
from __future__ import annotations

from scripts.lib.lightstep_csv import build_rows, write_rows
from scripts.lib.lightstep_export_checks import check_output, check_parts_complete

COLUMNS = ("a", "min", "max", "avg", "sum", "value")
PARTS = [[{"group-labels": ["a=1"], "points": [[1, 1]]}], [{"group-labels": ["a=1"], "points": [[2, 1]]}, {"group-labels": ["a=2"], "points": [[2, 1]]}]]


def test_complete_parts_pass_and_gaps_are_reported():
    assert check_parts_complete([[], []]) == []
    assert check_parts_complete([[], None]) == ["part 2 is missing or failed verification"]


def test_output_matching_distinct_label_sets_passes(tmp_path):
    path = tmp_path / "f.csv"
    write_rows(path, build_rows([{"group-labels": ["a=1"], "points": []}, {"group-labels": ["a=2"], "points": []}], COLUMNS))
    assert check_output(path, COLUMNS, PARTS, derived=False) == []


def test_output_row_count_header_and_bom_problems(tmp_path):
    path = tmp_path / "f.csv"
    write_rows(path, build_rows([{"group-labels": ["a=1"], "points": []}], COLUMNS))
    assert "1 rows but the parts hold 2" in check_output(path, COLUMNS, PARTS, derived=False)[0]
    assert "header differs" in check_output(path, ("b", *COLUMNS[1:]), PARTS, derived=False)[0]
    assert check_output(path, COLUMNS, PARTS, derived=True) == []
    path.write_text("no bom", encoding="utf-8")
    assert "could not be re-read" in check_output(path, COLUMNS, PARTS, derived=False)[0]
