"""Writes Lightstep timeseries as UI-format CSV: UTF-8 BOM, every field quoted, group columns then stats.

Pure row-building functions plus one atomic writer; no network. File names follow the ``combine_lightstep_parts.py``
convention (``<date>_<kind>.csv``, or ``<date>_<NN>_<kind>.csv`` only when a kind has to be split).
"""

from __future__ import annotations

import csv
import io
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path

STAT_COLUMNS = ("min", "max", "avg", "sum", "value")
_BOM = "\ufeff"


class FileExistsRefused(FileExistsError):
    """The target file exists and ``force`` was not set."""


def part_file_name(date: str, suffix: str, part: int | None = None) -> str:
    """Returns ``<date>_<suffix>.csv``, or ``<date>_<NN>_<suffix>.csv`` for numbered part ``part`` (>= 1)."""
    if part is None:
        return f"{date}_{suffix}.csv"
    if part < 1:
        raise ValueError("part numbers start at 1")
    return f"{date}_{part:02d}_{suffix}.csv"


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def _point_value(point: object) -> float | None:
    raw = point[1] if isinstance(point, (list, tuple)) else point
    return None if raw is None else float(raw)  # type: ignore[arg-type]


def _parse_labels(labels: Sequence[object]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for label in labels:
        name, separator, value = str(label).partition("=")
        if not separator:
            raise ValueError(f"group label {label!r} is not in 'name=value' form")
        parsed[name] = value
    return parsed


def series_to_row(series: dict[str, object], group_columns: Sequence[str]) -> list[str]:
    """Maps one series to ``group_columns`` values followed by ``min, max, avg, sum`` and an empty ``value``."""
    labels = _parse_labels(series.get("group-labels", []))  # type: ignore[arg-type]
    unknown = set(labels) - set(group_columns)
    if unknown:
        raise ValueError(f"series has labels not in the column set: {sorted(unknown)}")
    values = [v for v in map(_point_value, series.get("points", [])) if v is not None]  # type: ignore[arg-type]
    if values:
        total = sum(values)
        stats = [_format_number(x) for x in (min(values), max(values), total / len(values), total)]
    else:
        stats = ["", "", "", ""]
    return [*(labels.get(column, "") for column in group_columns), *stats, ""]


def build_rows(series: Sequence[dict[str, object]], columns: Sequence[str]) -> list[list[str]]:
    """Returns the header plus one row per series; ``columns`` must end with the stat columns."""
    if tuple(columns[-len(STAT_COLUMNS):]) != STAT_COLUMNS:
        raise ValueError(f"columns must end with {STAT_COLUMNS}")
    group_columns = list(columns[: -len(STAT_COLUMNS)])
    return [list(columns), *(series_to_row(item, group_columns) for item in series)]


def _current_umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


def write_rows(path: Path, rows: Sequence[Sequence[str]], *, force: bool = False) -> None:
    """Writes ``rows`` UI-style (BOM, all fields quoted) via a temp file renamed into place.

    Raises ``FileExistsRefused`` when ``path`` exists and ``force`` is false; the existing file is left untouched.
    """
    if path.exists() and not force:
        raise FileExistsRefused(f"{path} already exists; pass force=True to overwrite")
    buffer = io.StringIO()
    csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(rows)
    # The UI export has LF line endings and no trailing newline.
    text = _BOM + buffer.getvalue().removesuffix("\n")
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.chmod(temp_name, 0o666 & ~_current_umask())
        if force:
            os.replace(temp_name, path)
        else:
            try:
                os.link(temp_name, path)  # fails if another writer created the file since the check
            except FileExistsError:
                raise FileExistsRefused(f"{path} already exists; pass force=True to overwrite") from None
            os.unlink(temp_name)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def write_series_csv(
    path: Path, series: Sequence[dict[str, object]], columns: Sequence[str], *, force: bool = False
) -> int:
    """Builds and writes the CSV for ``series``; returns the number of data rows written."""
    rows = build_rows(series, columns)
    write_rows(path, rows, force=force)
    return len(rows) - 1
