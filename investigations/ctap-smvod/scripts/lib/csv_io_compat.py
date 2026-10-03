"""Compatibility wrappers that route script-local CSV reads/writes through `src.lib.csv_io`."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter


class DictReader(Iterator[dict[str, str]]):
    """Minimal `csv.DictReader`-compatible iterator backed by `CsvFileReader`."""

    def __init__(self, handle: Any) -> None:
        rows = list(CsvFileReader().read_rows(handle.name))
        self._rows = [self._strip_bom_keys(row) for row in rows]
        self._index = 0
        self.fieldnames = list(self._rows[0].keys()) if self._rows else None

    def __iter__(self) -> DictReader:
        return self

    def __next__(self) -> dict[str, str]:
        if self._index >= len(self._rows):
            raise StopIteration
        row = self._rows[self._index]
        self._index += 1
        return row

    @staticmethod
    def _strip_bom_keys(row: dict[str, str]) -> dict[str, str]:
        if None in row:
            raise ValueError("CSV row has more columns than the header defines")
        return {key.lstrip("\ufeff"): value for key, value in row.items()}


class DictWriter:
    """Minimal `csv.DictWriter`-compatible buffer backed by `CsvFileWriter`."""

    def __init__(self, handle: Any, fieldnames: list[str], extrasaction: str = "raise") -> None:
        self._handle = handle
        self.fieldnames = fieldnames
        self._extrasaction = extrasaction
        self._rows: list[dict[str, str]] = []
        self._header_requested = False
        self._flushed = False
        original_close = handle.close

        def close_with_flush() -> Any:
            self._flush()
            return original_close()

        handle.close = close_with_flush

    def writeheader(self) -> None:
        self._header_requested = True

    def writerow(self, row: dict[str, Any]) -> None:
        self._rows.append(self._normalize_row(row))

    def writerows(self, rows: Iterable[dict[str, Any]]) -> None:
        for row in rows:
            self.writerow(row)

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, str]:
        extras = [key for key in row if key not in self.fieldnames]
        if extras and self._extrasaction != "ignore":
            raise ValueError(f"unexpected fields for DictWriter: {extras}")
        normalized: dict[str, str] = {}
        for field in self.fieldnames:
            value = row.get(field, "")
            normalized[field] = "" if value is None else str(value)
        return normalized

    def _flush(self) -> None:
        if self._flushed:
            return
        self._flushed = True
        CsvFileWriter().write_rows(self._handle.name, self._rows, self.fieldnames)
