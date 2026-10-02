"""Tests for `src.lib.csv_io.protocols`."""
from __future__ import annotations

from collections.abc import Iterator

from src.lib.csv_io.protocols import CsvReaderProtocol, CsvWriterProtocol


class _ConformingReader:
    def read_rows(self, path: str) -> Iterator[dict[str, str]]:
        yield {}


class _ConformingWriter:
    def write_rows(self, path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        return None


def test_conforming_reader_satisfies_protocol() -> None:
    assert isinstance(_ConformingReader(), CsvReaderProtocol)


def test_conforming_writer_satisfies_protocol() -> None:
    assert isinstance(_ConformingWriter(), CsvWriterProtocol)


def test_reader_and_writer_protocols_are_independent() -> None:
    reader = _ConformingReader()
    writer = _ConformingWriter()

    assert isinstance(reader, CsvReaderProtocol)
    assert not isinstance(reader, CsvWriterProtocol)
    assert isinstance(writer, CsvWriterProtocol)
    assert not isinstance(writer, CsvReaderProtocol)
