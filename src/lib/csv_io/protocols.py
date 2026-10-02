"""Protocol skeletons for raw CSV I/O (distinct from `report_render`'s formatted-output Strategy).

See `docs/plan/src-lib-migration/csv-io-lib-migration/stories.md` CIM-1. Split into two separate
`Protocol`s per PYTHON_DESIGN.md's ISP trigger: a read-only consumer never needs `write_rows`, and
vice versa, so one combined `CsvIoProtocol` would force unused methods on either side.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class CsvReaderProtocol(Protocol):
    """DIP seam: read a CSV file's rows as dicts, keyed by header column."""

    def read_rows(self, path: str) -> Iterator[dict[str, str]]:
        ...


@runtime_checkable
class CsvWriterProtocol(Protocol):
    """DIP seam: write rows (dicts) to a CSV file under a caller-supplied header."""

    def write_rows(self, path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        ...
