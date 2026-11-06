"""Load daily files for a date range from the local data sources and report the gaps."""
from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from src.lib.csv_io.csv_file import CsvFileReader
from src.lib.paths import YamlPathResolver

SLUG = "shaka-6001"
CTAP_SLUG = "ctap-smvod"


class LocalDataError(Exception):
    """Raised for an invalid range or an unreadable local file."""


@dataclass(frozen=True)
class LoadResult:
    rows: list[dict[str, str]]
    found: dict[date, Path]
    missing: list[date]


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise LocalDataError(f"end date {end} is before start date {start}")
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def default_sources(resolver: YamlPathResolver, repo_root: Path, tenant: str) -> list[Path]:
    """The four local sources, in lookup order."""
    return [
        resolver.resolve_investigation_data_dir(SLUG, "athena", tenant=tenant),
        resolver.resolve_investigation_data_dir(CTAP_SLUG, "athena", tenant=tenant),
        resolver.resolve_investigation_output_dir(CTAP_SLUG, tenant=tenant),
        repo_root / "output" / tenant,
    ]


def daily_filename(day: date, artifact: str) -> str:
    return f"{day.isoformat()}_{artifact}.csv"


def find_daily_file(sources: Sequence[Path], day: date, artifact: str) -> Path | None:
    """First source holding a non-empty file for ``day``; a zero-byte file counts as absent."""
    for directory in sources:
        candidate = directory / daily_filename(day, artifact)
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise LocalDataError(f"cannot read {path}: {exc}") from exc


def load_daily(sources: Sequence[Path], artifact: str, dates: Sequence[date]) -> LoadResult:
    """Rows of every date found (first source wins per date) plus the dates found nowhere."""
    rows: list[dict[str, str]] = []
    found: dict[date, Path] = {}
    missing: list[date] = []
    for day in dates:
        path = find_daily_file(sources, day, artifact)
        if path is None:
            missing.append(day)
            continue
        found[day] = path
        rows.extend(_read_rows(path))
    return LoadResult(rows=rows, found=found, missing=missing)
