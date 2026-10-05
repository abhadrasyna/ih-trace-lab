"""Tests for `MonthlyCsvStore`'s date-keyed upsert behavior."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter
from src.lib.csv_io.monthly_store import MonthlyCsvStore


def _store() -> MonthlyCsvStore:
    return MonthlyCsvStore(CsvFileReader(), CsvFileWriter())


def test_replace_date_creates_new_month_file(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"

    _store().replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    assert path.read_text(encoding="utf-8") == "session_date,Home\n2026-08-01,7\n"


def test_replace_date_appends_a_new_day_without_touching_others(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    store.replace_date(path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "9"}])

    assert list(CsvFileReader().read_rows(str(path))) == [
        {"session_date": "2026-08-01", "Home": "7"},
        {"session_date": "2026-08-02", "Home": "9"},
    ]


def test_replace_date_overwrites_rerun_of_same_day_without_duplicating(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "8"}])

    assert list(CsvFileReader().read_rows(str(path))) == [{"session_date": "2026-08-01", "Home": "8"}]


def test_replace_date_supports_multiple_rows_per_day_long_format(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_shaka-error-hhid.csv"
    store = _store()

    store.replace_date(
        path,
        "2026-08-01",
        [
            {"session_date": "2026-08-01", "errorcode": "1001", "metric_value": "2"},
            {"session_date": "2026-08-01", "errorcode": "1003", "metric_value": "4"},
        ],
    )

    assert list(CsvFileReader().read_rows(str(path))) == [
        {"session_date": "2026-08-01", "errorcode": "1001", "metric_value": "2"},
        {"session_date": "2026-08-01", "errorcode": "1003", "metric_value": "4"},
    ]


def test_replace_date_appends_new_columns_seen_in_later_rows(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    store.replace_date(path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "9", "Away": "3"}])

    rows = list(CsvFileReader().read_rows(str(path)))
    assert rows == [
        {"session_date": "2026-08-01", "Home": "7", "Away": ""},
        {"session_date": "2026-08-02", "Home": "9", "Away": "3"},
    ]


def test_replace_date_sorts_rows_chronologically_regardless_of_insertion_order(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-05", [{"session_date": "2026-08-05", "Home": "1"}])

    store.replace_date(path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "2"}])

    assert [row["session_date"] for row in CsvFileReader().read_rows(str(path))] == ["2026-08-02", "2026-08-05"]


def test_replace_date_keeps_canonical_column_order_when_a_day_omits_a_column(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    # Day 1's rows omit "Away" entirely (e.g. that metric's query returned no data that day).
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}], field_order=["session_date", "Home", "Away"])

    store.replace_date(
        path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "9", "Away": "3"}], field_order=["session_date", "Home", "Away"]
    )

    with path.open(encoding="utf-8") as handle:
        assert handle.readline().strip() == "session_date,Home,Away"


def test_replace_date_rejects_rows_missing_the_date_field(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"

    with pytest.raises(ValueError, match="session_date"):
        _store().replace_date(path, "2026-08-01", [{"Home": "7"}])


def test_replace_date_rejects_rows_whose_date_field_mismatches_date_value(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"

    with pytest.raises(ValueError, match="2026-08-01"):
        _store().replace_date(path, "2026-08-01", [{"session_date": "2026-08-02", "Home": "7"}])


def test_replace_date_leaves_no_leftover_temp_file_on_success(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"

    _store().replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    remaining_names = {entry.name for entry in tmp_path.iterdir()}
    assert remaining_names == {path.name, f"{path.name}.lock"}


def test_replace_date_does_not_corrupt_existing_file_if_writer_fails(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])
    original_content = path.read_text(encoding="utf-8")

    class FailingWriter:
        def write_rows(self, *_args, **_kwargs) -> None:
            raise RuntimeError("disk full")

    failing_store = MonthlyCsvStore(CsvFileReader(), FailingWriter())
    with pytest.raises(RuntimeError, match="disk full"):
        failing_store.replace_date(path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "9"}])

    assert path.read_text(encoding="utf-8") == original_content
    remaining_names = {entry.name for entry in tmp_path.iterdir()}
    assert remaining_names == {path.name, f"{path.name}.lock"}


def test_replace_date_creates_a_new_file_as_world_readable(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"

    _store().replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])

    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode & stat.S_IRGRP and mode & stat.S_IROTH


def test_replace_date_preserves_an_existing_files_permissions(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()
    store.replace_date(path, "2026-08-01", [{"session_date": "2026-08-01", "Home": "7"}])
    os.chmod(path, 0o664)

    store.replace_date(path, "2026-08-02", [{"session_date": "2026-08-02", "Home": "9"}])

    assert stat.S_IMODE(path.stat().st_mode) == 0o664


def test_replace_date_serializes_concurrent_runs_so_neither_days_rows_are_lost(tmp_path: Path) -> None:
    import threading

    path = tmp_path / "2026-08_adoption-report.csv"
    store = _store()

    def _run(date_value: str, value: str) -> None:
        store.replace_date(path, date_value, [{"session_date": date_value, "Home": value}])

    threads = [
        threading.Thread(target=_run, args=("2026-08-01", "7")),
        threading.Thread(target=_run, args=("2026-08-02", "9")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    rows = list(CsvFileReader().read_rows(str(path)))
    assert {row["session_date"] for row in rows} == {"2026-08-01", "2026-08-02"}




def test_replace_date_supports_a_custom_date_field(tmp_path: Path) -> None:
    path = tmp_path / "2026-08_custom.csv"
    store = MonthlyCsvStore(CsvFileReader(), CsvFileWriter(), date_field="report_date")

    store.replace_date(path, "2026-08-01", [{"report_date": "2026-08-01", "Home": "7"}])

    assert list(CsvFileReader().read_rows(str(path))) == [{"report_date": "2026-08-01", "Home": "7"}]
