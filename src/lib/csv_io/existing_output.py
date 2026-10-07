"""Pre-flight check: does a report CSV already hold the data an Athena query would produce?

Callers run this before firing any Athena query so a re-run of an already-produced date does not
re-spend a query. A header-only or missing file counts as "not produced" so a failed or empty
earlier run is retried.
"""
from __future__ import annotations

from pathlib import Path

from src.lib.csv_io.protocols import CsvReaderProtocol

_DATE_FIELD = "session_date"


def csv_has_data(reader: CsvReaderProtocol, path: Path, *, date_value: str | None = None, date_field: str = _DATE_FIELD) -> bool:
    """True if `path` exists and has a data row (for `date_value` in `date_field`, when given)."""
    if not path.is_file():
        return False
    for row in reader.read_rows(str(path)):
        if date_value is None or row.get(date_field) == date_value:
            return True
    return False
