"""Load and group flattened PLAYER_ERROR event files (one row = one event, keyed on ``messageid``)."""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

FILE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<code>.+)\.csv$")
REQUIRED_COLUMNS = ("messageid", "sessionId", "errorcode")


def find_files(input_dir: Path, code: str) -> list[tuple[str, Path]]:
    """Return ``(date, path)`` for every ``<date>_<code>.csv`` in ``input_dir``, sorted by date."""
    found = []
    for path in sorted(input_dir.glob(f"*_{code}.csv")):
        match = FILE_RE.match(path.name)
        if match and match.group("code") == code:
            found.append((match.group("date"), path))
    if not found:
        raise FileNotFoundError(f"no *_{code}.csv files in {input_dir}")
    return found


def select_files(files: list[tuple[str, Path]], dates: list[str] | None) -> list[tuple[str, Path]]:
    """Restrict ``files`` to ``dates``; a requested date with no file is an error, not silent no-data."""
    if not dates:
        return files
    available = {date for date, _ in files}
    missing = [date for date in dates if date not in available]
    if missing:
        raise FileNotFoundError(f"no file for requested dates {missing}")
    return [(date, path) for date, path in files if date in dates]


def read_events(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one flattened file; fail loudly when the identity columns are missing."""
    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing:
            raise ValueError(f"{path.name}: missing required columns {missing}")
        return header, list(reader)


def dedupe_events(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the first row per ``messageid``; a blank messageid is an error, not a silent drop."""
    seen: set[str] = set()
    kept = []
    for row in rows:
        message_id = (row.get("messageid") or "").strip()
        if not message_id:
            raise ValueError("row with blank messageid cannot be deduplicated")
        if message_id not in seen:
            seen.add(message_id)
            kept.append(row)
    return kept


def distinct_count(rows: list[dict[str, str]], column: str) -> int:
    """Distinct non-blank values of ``column``."""
    return len({(row.get(column) or "").strip() for row in rows} - {""})


def sessions_per_group(rows: list[dict[str, str]], group_col: str) -> dict[str, int]:
    """Distinct sessionId count per ``group_col`` value (blank group values are skipped)."""
    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        key = (row.get(group_col) or "").strip()
        session = (row.get("sessionId") or "").strip()
        if key and session:
            groups[key].add(session)
    return {key: len(sessions) for key, sessions in groups.items()}
