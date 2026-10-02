"""`CsvReaderProtocol`/`CsvWriterProtocol` conformance tests for the concrete `csv_file` implementers."""
from __future__ import annotations

from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter
from src.lib.csv_io.protocols import CsvReaderProtocol, CsvWriterProtocol


def test_csv_file_reader_satisfies_csv_reader_protocol() -> None:
    assert isinstance(CsvFileReader(), CsvReaderProtocol)


def test_csv_file_writer_satisfies_csv_writer_protocol() -> None:
    assert isinstance(CsvFileWriter(), CsvWriterProtocol)
