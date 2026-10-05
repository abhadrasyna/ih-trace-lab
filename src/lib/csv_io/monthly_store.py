"""Date-keyed monthly CSV store for reports that append one day's rows at a time.

Distinct from `report_render` (formatted-output rendering) and the rest of `csv_io` (raw,
whole-file read/write): this module owns the "add today's rows to an existing month file"
upsert semantics that `aws-access-cli`'s daily adoption/Shaka-error reports need, ported from the
pre-migration `AdoptionReportStore`'s date-merge behavior (see `docs/archive/src-lib-migration/`).

Works for both row shapes those reports produce: one row per date (adoption reports, wide
columns) and multiple rows per date (Shaka error reports, long format, one row per error code).
Either way, `replace_date` drops any existing rows for the given date before appending the new
ones, so re-running the same day's report never duplicates rows.
"""
from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import tempfile
from pathlib import Path

from src.lib.csv_io.protocols import CsvReaderProtocol, CsvWriterProtocol

_DATE_FIELD = "session_date"
_DEFAULT_FILE_MODE = 0o644


class MonthlyCsvStore:
    """Upserts a single date's rows into a month-scoped CSV file."""

    def __init__(self, reader: CsvReaderProtocol, writer: CsvWriterProtocol, *, date_field: str = _DATE_FIELD) -> None:
        self._reader = reader
        self._writer = writer
        self._date_field = date_field

    def replace_date(
        self,
        path: Path,
        date_value: str,
        rows: list[dict[str, str]],
        *,
        field_order: list[str] | None = None,
    ) -> Path:
        """Upserts `date_value`'s `rows` into the month file at `path`.

        Existing rows for `date_value` are dropped first; rows for every other date in the
        file are preserved. Column order starts from `field_order` (the caller's canonical
        column order, e.g. a fixed metric list -- pass this so column order stays stable even
        if an earlier day's rows happened to omit a column a later day introduces), falls back
        to the existing file's headers if `field_order` is omitted, then any further new column
        introduced by `rows` is appended at the end. The combined rows are written back sorted
        by the date field so the file reads chronologically regardless of run order. The whole
        read-merge-write is held under an exclusive lock on a sibling `.lock` file, so two runs
        for the same month file (e.g. a parallel backfill of two different days) can't both read
        the pre-update file and have the slower one overwrite the faster one's rows. The write
        itself goes to a sibling temp file first, then `os.replace`s `path` atomically, so a
        crash or interrupted write mid-save can never leave `path` half-written/corrupted. The
        temp file's permissions are set to match the existing file's (or `_DEFAULT_FILE_MODE` for
        a brand-new file) before the swap, since `os.replace` keeps whatever mode the temp file
        had -- without this, `tempfile.mkstemp`'s owner-only `0600` would make every rerun
        progressively lock the file away from any other user/process that needs to read it.

        Raises:
            ValueError: If any row in `rows` is missing the date field, or carries a date field
                value other than `date_value` -- either is a schema/caller mismatch that would
                otherwise silently fail to replace the right rows (or duplicate them) on a rerun.
        """
        mismatched_rows = [row for row in rows if row.get(self._date_field) != date_value]
        if mismatched_rows:
            raise ValueError(f"every row's {self._date_field!r} must equal {date_value!r}; got {mismatched_rows[0]!r}")

        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f"{path.name}.lock")
        with lock_path.open("a+") as lock_file, _exclusive_lock(lock_file):
            existing_rows = list(self._reader.read_rows(str(path))) if path.is_file() else []
            fieldnames = list(field_order) if field_order is not None else (list(existing_rows[0].keys()) if existing_rows else [])
            for row in [*existing_rows, *rows]:
                for key in row:
                    if key not in fieldnames:
                        fieldnames.append(key)

            kept_rows = [row for row in existing_rows if row.get(self._date_field) != date_value]
            combined_rows = sorted(kept_rows + rows, key=lambda row: row.get(self._date_field, ""))

            file_mode = stat.S_IMODE(path.stat().st_mode) if path.is_file() else _DEFAULT_FILE_MODE
            fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            os.close(fd)
            try:
                os.chmod(tmp_name, file_mode)
                self._writer.write_rows(tmp_name, combined_rows, fieldnames)
                os.replace(tmp_name, path)
            except BaseException:
                os.unlink(tmp_name)
                raise
        return path


@contextlib.contextmanager
def _exclusive_lock(lock_file):
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
