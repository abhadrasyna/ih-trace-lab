"""Pure logic for comparing hand-exported Lightstep CSVs with API-generated ones, by key set (not row count)."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

STAT_COLUMNS = ("min", "max", "avg", "sum", "value")
SMVOD_TS_KEY = ("sessionId",)


@dataclass(frozen=True)
class KindComparison:
    kind: str
    manual_keys: int
    generated_keys: int
    both: int
    only_manual: int
    only_generated: int
    sum_equal: int
    sum_different: int
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]

    @property
    def only_manual_pct(self) -> float:
        return 100 * self.only_manual / self.manual_keys if self.manual_keys else 0.0

    @property
    def only_generated_pct(self) -> float:
        return 100 * self.only_generated / self.manual_keys if self.manual_keys else 0.0


def find_files(directory: Path, date: str, kind: str) -> list[Path]:
    """The combined file when it exists (it already contains the parts), else the numbered parts."""
    combined = directory / f"{date}_{kind}.csv"
    if combined.is_file():
        return [combined]
    return sorted(directory.glob(f"{date}_[0-9][0-9]_{kind}.csv"))


def read_rows(paths: Iterable[Path]) -> tuple[list[str], list[dict[str, str]]]:
    """Reads CSV files (BOM tolerant); returns the first header and every row as a dict."""
    header: list[str] = []
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, restkey="__extra__")
            current = list(reader.fieldnames or [])
            if header and current != header:
                raise ValueError(f"{path}: header {current} differs from {header}")
            header = current
            for row in reader:
                if "__extra__" in row or None in row.values():
                    raise ValueError(f"{path}: ragged row at line {reader.line_num}")
                rows.append(row)
    return header, rows


def _normalise(value: str) -> str:
    return value[1:] if value.startswith("'") else value  # the UI prefixes values starting with '-' with an apostrophe


def key_columns(header: Sequence[str], kind: str) -> tuple[str, ...]:
    if kind == "smvod-ts":
        return SMVOD_TS_KEY
    return tuple(column for column in header if column not in STAT_COLUMNS)


def keyed_sums(rows: Iterable[dict[str, str]], columns: Sequence[str], unique: bool = True) -> dict[tuple[str, ...], str]:
    """Maps key -> sum; with ``unique`` a repeated key raises, since its sum would be silently overwritten."""
    keyed: dict[tuple[str, ...], str] = {}
    for row in rows:
        key = tuple(_normalise(row.get(c, "")) for c in columns)
        if unique and key in keyed:
            raise ValueError(f"duplicate key {key} over columns {list(columns)}")
        keyed[key] = _normalise(row.get("sum", ""))
    return keyed


def _same_sum(a: str, b: str) -> bool:
    try:
        return float(a) == float(b)
    except ValueError:
        return a == b


def compare_kind(kind: str, manual: tuple[list[str], list[dict[str, str]]], generated: tuple[list[str], list[dict[str, str]]]) -> KindComparison:
    """Compares key sets over the columns both files share (all non-stat columns; ``sessionId`` for smvod-ts)."""
    (m_header, m_rows), (g_header, g_rows) = manual, generated
    shared = tuple(c for c in key_columns(m_header, kind) if c in g_header)
    if kind != "smvod-ts" and not ("sum" in m_header and "sum" in g_header):
        raise ValueError(f"{kind}: a 'sum' column is required on both sides")
    if not shared:
        raise ValueError(f"{kind}: no shared key columns between {m_header} and {g_header}")
    unique = kind != "smvod-ts"
    m_keys, g_keys = keyed_sums(m_rows, shared, unique), keyed_sums(g_rows, shared, unique)
    both = m_keys.keys() & g_keys.keys()
    equal = sum(1 for key in both if _same_sum(m_keys[key], g_keys[key])) if kind != "smvod-ts" else 0
    return KindComparison(
        kind=kind,
        manual_keys=len(m_keys),
        generated_keys=len(g_keys),
        both=len(both),
        only_manual=len(m_keys.keys() - g_keys.keys()),
        only_generated=len(g_keys.keys() - m_keys.keys()),
        sum_equal=equal,
        sum_different=len(both) - equal if kind != "smvod-ts" else 0,
        missing_columns=tuple(c for c in m_header if c not in g_header),
        extra_columns=tuple(c for c in g_header if c not in m_header),
    )


def format_report(results: Sequence[KindComparison]) -> str:
    lines = [f"{'kind':20} {'manual':>7} {'generated':>9} {'both':>7} {'only_manual':>11} {'only_generated':>14} {'sum_diff':>8}"]
    for r in results:
        lines.append(
            f"{r.kind:20} {r.manual_keys:7d} {r.generated_keys:9d} {r.both:7d} "
            f"{r.only_manual:6d} ({r.only_manual_pct:4.1f}%) {r.only_generated:7d} ({r.only_generated_pct:4.1f}%) {r.sum_different:8d}"
        )
        if r.missing_columns or r.extra_columns:
            lines.append(f"  columns only in manual: {list(r.missing_columns)}; only in generated: {list(r.extra_columns)}")
    lines.append("percentages are relative to the manual key count; sum_diff is not computed for smvod-ts")
    return "\n".join(lines)
