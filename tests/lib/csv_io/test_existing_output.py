"""Tests for `csv_has_data`."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.lib.csv_io.csv_file import CsvFileReader
from src.lib.csv_io.existing_output import csv_date_needs_retry, csv_has_data


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


def _blank_row_csv(tmp_path: Path, row: str, name: str = "b.csv") -> Path:
    path = tmp_path / name
    path.write_text(f"session_date,Home,Attempts\n{row}\n", encoding="utf-8")
    return path


def test_retry_when_recent_row_has_blank_cell(tmp_path: Path) -> None:
    path = _blank_row_csv(tmp_path, "2026-10-15,,5")

    assert csv_date_needs_retry(CsvFileReader(), path, date_value="2026-10-15", retry_days=3, today=date(2026, 10, 17))


def test_no_retry_when_row_complete_old_or_disabled(tmp_path: Path) -> None:
    complete = _blank_row_csv(tmp_path, "2026-10-15,7,5", "complete.csv")
    blank = _blank_row_csv(tmp_path, "2026-10-10,,5", "blank.csv")
    today = date(2026, 10, 17)

    assert not csv_date_needs_retry(CsvFileReader(), complete, date_value="2026-10-15", retry_days=3, today=today)
    assert not csv_date_needs_retry(CsvFileReader(), blank, date_value="2026-10-10", retry_days=3, today=today)
    assert not csv_date_needs_retry(CsvFileReader(), blank, date_value="2026-10-10", retry_days=0, today=today)
