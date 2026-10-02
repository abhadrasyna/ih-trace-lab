"""Tests for `src.lib.csv_io.csv_file`."""
from __future__ import annotations

from pathlib import Path

from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample.csv"


def test_reader_reads_expected_rows() -> None:
    rows = list(CsvFileReader().read_rows(str(_FIXTURE_PATH)))

    assert rows == [
        {"name": "alice", "count": "3"},
        {"name": "bob", "count": "5"},
    ]


def test_writer_writes_expected_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "out.csv"
    rows = [
        {"name": "carol", "count": "7"},
        {"name": "dave", "count": "1"},
    ]

    CsvFileWriter().write_rows(str(out_path), rows, fieldnames=["name", "count"])

    round_tripped = list(CsvFileReader().read_rows(str(out_path)))
    assert round_tripped == rows


def test_round_trip_write_then_read(tmp_path: Path) -> None:
    out_path = tmp_path / "round_trip.csv"
    rows = [{"name": "erin", "count": "9"}]

    CsvFileWriter().write_rows(str(out_path), rows, fieldnames=["name", "count"])

    assert list(CsvFileReader().read_rows(str(out_path))) == rows


def test_reader_raises_on_missing_file() -> None:
    missing_path = "/nonexistent/path/does-not-exist.csv"

    try:
        list(CsvFileReader().read_rows(missing_path))
        raise AssertionError("expected FileNotFoundError for a missing path")
    except FileNotFoundError:
        pass
