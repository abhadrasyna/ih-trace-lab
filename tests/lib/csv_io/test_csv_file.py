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
