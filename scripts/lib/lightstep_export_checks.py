"""Pure sanity checks run on an exported kind before its part files are deleted.

Each function returns a list of problems (empty means the check passed); nothing here touches the network
or deletes anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from scripts.lib.lightstep_csv import read_rows
from scripts.lib.lightstep_stitch import stitch_series

Series = dict[str, object]


def check_parts_complete(loaded: Sequence[Sequence[Series] | None]) -> list[str]:
    """(a) Every expected window has a verified part. Windows are numbered uniquely, so duplicates cannot occur;
    leftover files from an earlier ``--part-hours`` are outside the expected numbering and ignored."""
    return [f"part {i} is missing or failed verification" for i, part in enumerate(loaded, start=1) if part is None]


def check_output(path: Path, header: Sequence[str], parts: Sequence[Sequence[Series]], *, derived: bool) -> list[str]:
    """(b)+(c) Re-reads the written file; checks BOM, header and that the row count matches the parts.

    A plain kind has one row per distinct label set across the parts; a derived kind (``smvod-ts``) drops
    series without a usable point, so it may have fewer rows but never more.
    """
    try:
        rows = read_rows(path)
    except (OSError, ValueError) as exc:
        return [f"{path.name} could not be re-read: {exc}"]
    if not rows:
        return [f"{path.name} has no rows"]
    problems = []
    if rows[0] != list(header):
        problems.append(f"{path.name} header differs from the expected columns")
    distinct, written = len(stitch_series(parts)), len(rows) - 1
    if (derived and written > distinct) or (not derived and written != distinct):
        problems.append(f"{path.name} has {written} rows but the parts hold {distinct} distinct label sets")
    return problems
