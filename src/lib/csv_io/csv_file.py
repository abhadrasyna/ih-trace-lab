"""Stdlib-backed concrete implementers of `CsvReaderProtocol`/`CsvWriterProtocol`.

See `docs/plan/src-lib-migration/csv-io-lib-migration/stories.md` CIM-2. Per this story's locked-in
decision, CSV edge-case behavior (ordering, quoting, encoding, newline handling) matches
`csv.DictReader`/`csv.DictWriter` defaults exactly -- no bespoke parsing/formatting is invented.
Neither class holds project-specific column/schema knowledge: `fieldnames` is always supplied by
the caller.
"""
from __future__ import annotations

import csv
from collections.abc import Iterator


class CsvFileReader:
    """`CsvReaderProtocol` implementer backed by `csv.DictReader`."""

    def read_rows(self, path: str) -> Iterator[dict[str, str]]:
        # newline="" per the csv module's own documented recommendation, so it can handle
        # embedded newlines/line terminators itself rather than the platform's text-mode translation.
        # utf-8-sig (not plain utf-8): a leading BOM must be stripped *before* csv parsing sees the
        # line, otherwise a BOM immediately followed by a quote (`\ufeffx"col"`) isn't recognized as
        # the start of a quoted field -- the quote marks end up as literal characters in the first
        # field's name/value instead of being parsed away. Seen in real Lightstep CSV exports whose
        # first column is both BOM-prefixed and quoted (e.g. `"error_flag"` as the first header),
        # which silently produced a mangled `'"error_flag"'` key and made every downstream lookup of
        # that field return the fallback default.
        with open(path, newline="", encoding="utf-8-sig") as handle:
            yield from csv.DictReader(handle)


class CsvFileWriter:
    """`CsvWriterProtocol` implementer backed by `csv.DictWriter`."""

    def write_rows(self, path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
