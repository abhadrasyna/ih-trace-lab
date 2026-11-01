"""Derive the approximate ``smvod-ts`` rows from ``smvod`` series sampled at a 1 s output period.

The public API has no span-sample endpoint, so ``oldest_micros``/``youngest_micros`` are the first and last
non-zero point timestamps of each series (session coverage only). Columns the points cannot supply
(``error_flag``, ``component_name``, ``span_name``, ``duration_millis``) are written empty.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from scripts.lib.lightstep_csv import parse_labels

Series = dict[str, object]


def _micros(stamp: object) -> int:
    if isinstance(stamp, str):
        return int(datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp() * 1_000_000)
    return int(float(stamp) * 1000)  # type: ignore[arg-type]  # API point timestamps are epoch milliseconds


def point_bounds(series: Series) -> tuple[int, int] | None:
    """Returns (oldest, youngest) epoch microseconds over the non-zero points, or None when there are none."""
    stamps = [
        _micros(point[0])
        for point in series.get("points", [])  # type: ignore[attr-defined]
        if isinstance(point, (list, tuple)) and point[1]
    ]
    return (min(stamps), max(stamps)) if stamps else None


def derive_rows(series: Sequence[Series], columns: Sequence[str]) -> list[list[str]]:
    """Returns the header plus one row per series that has a non-zero point.

    ``columns`` is the ``smvod-ts`` column list; any column that is not a series label and not
    ``oldest_micros``/``youngest_micros`` is left empty.
    """
    rows = [list(columns)]
    for item in series:
        bounds = point_bounds(item)
        if bounds is None:
            continue
        values = {**parse_labels(item.get("group-labels", [])), "oldest_micros": str(bounds[0]), "youngest_micros": str(bounds[1])}  # type: ignore[arg-type]
        rows.append([values.get(column, "") for column in columns])
    return rows
