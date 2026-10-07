"""Tests for `csv_has_data`."""
from __future__ import annotations

from pathlib import Path

from src.lib.csv_io.csv_file import CsvFileReader
from src.lib.csv_io.existing_output import csv_has_data


def test_true_when_file_has_a_row_for_the_date(tmp_path: Path) -> None:
    path = tmp_path / "r.csv"
    path.write_text("session_date,Home\n2026-08-01,7\n", encoding="utf-8")

    assert csv_has_data(CsvFileReader(), path, date_value="2026-08-01")
    assert csv_has_data(CsvFileReader(), path)


def test_false_for_missing_file_header_only_file_or_other_date(tmp_path: Path) -> None:
    header_only = tmp_path / "h.csv"
    header_only.write_text("session_date,Home\n", encoding="utf-8")
    other_date = tmp_path / "o.csv"
    other_date.write_text("session_date,Home\n2026-08-02,7\n", encoding="utf-8")

    assert not csv_has_data(CsvFileReader(), tmp_path / "missing.csv")
    assert not csv_has_data(CsvFileReader(), header_only)
    assert not csv_has_data(CsvFileReader(), other_date, date_value="2026-08-01")
