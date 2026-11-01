"""Pure merge of per-window Lightstep results into one-day results; no I/O, no network.

``stitch_series`` merges raw series (exact). ``stitch_rows`` merges UI-format rows read back from part files:
``min``/``max``/``sum`` are exact, while ``avg`` is ``sum / count`` with each part's point count recovered as
``round(sum / avg)``. A part whose ``avg`` is 0 carries no recoverable count, so it is weighted with the most
common recovered count of the other parts (1 when there is none) and the merged ``avg`` is then approximate.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from scripts.lib.lightstep_csv import STAT_COLUMNS, format_number

Series = dict[str, object]
Row = list[str]
_STATS = 4  # min, max, avg, sum; the last stat column ("value") is carried as an empty string


class StitchError(ValueError):
    """Parts cannot be merged (different headers or malformed stats)."""


def _label_key(series: Series) -> tuple[str, ...]:
    return tuple(sorted(str(label) for label in series.get("group-labels", [])))  # type: ignore[attr-defined]


def _point_key(point: object) -> object:
    return point[0] if isinstance(point, (list, tuple)) and point else None


def stitch_series(parts: Sequence[Sequence[Series]]) -> list[Series]:
    """Merges series from several windows by label set; points are concatenated, de-duplicated by timestamp and sorted.

    Output order follows first appearance across ``parts``.
    """
    merged: dict[tuple[str, ...], Series] = {}
    for part in parts:
        for item in part:
            key = _label_key(item)
            target = merged.setdefault(key, {**item, "points": []})
            target["points"].extend(item.get("points", []))  # type: ignore[attr-defined]
    for target in merged.values():
        seen: set[object] = set()
        unique: list[object] = []
        for point in target["points"]:  # type: ignore[attr-defined]
            stamp = _point_key(point)
            if stamp is not None:
                if stamp in seen:
                    continue
                seen.add(stamp)
            unique.append(point)
        unique.sort(key=lambda p: (_point_key(p) is None, _point_key(p) or 0))
        target["points"] = unique
    return list(merged.values())


def _number(text: str) -> float | None:
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        raise StitchError(f"stat {text!r} is not a number") from None


def _recovered_count(total: float, average: float) -> int | None:
    return round(total / average) if average else None


def _merge_stats(entries: Sequence[tuple[float | None, ...]], default_count: int) -> list[str]:
    usable = [e for e in entries if e[0] is not None]
    if not usable:
        return ["", "", "", ""]
    count = 0
    for _low, _high, average, total in usable:
        recovered = _recovered_count(total, average) if average is not None and total is not None else None
        count += recovered if recovered else default_count
    grand_total = sum(e[3] for e in usable)  # type: ignore[misc]
    return [
        format_number(min(e[0] for e in usable)),  # type: ignore[type-var]
        format_number(max(e[1] for e in usable)),  # type: ignore[type-var]
        format_number(grand_total / count),
        format_number(grand_total),
    ]


def stitch_rows(parts: Sequence[Sequence[Row]]) -> list[Row]:
    """Merges UI-format row sets (header first) by group-column values and returns the header plus merged rows.

    Raises ``StitchError`` for no parts, differing headers, or a header that does not end with the stat columns.
    """
    if not parts:
        raise StitchError("no parts to stitch")
    header = list(parts[0][0]) if parts[0] else []
    if tuple(header[-len(STAT_COLUMNS):]) != STAT_COLUMNS:
        raise StitchError(f"header must end with {STAT_COLUMNS}")
    width = len(header) - len(STAT_COLUMNS)
    grouped: dict[tuple[str, ...], list[tuple[float | None, ...]]] = {}
    for part in parts:
        if not part or list(part[0]) != header:
            raise StitchError("parts have different headers")
        for row in part[1:]:
            stats = tuple(_number(cell) for cell in row[width : width + _STATS])
            grouped.setdefault(tuple(row[:width]), []).append(stats)
    default_count = _modal_count(grouped)
    return [header, *([*key, *_merge_stats(entries, default_count), ""] for key, entries in grouped.items())]


def _modal_count(grouped: dict[tuple[str, ...], list[tuple[float | None, ...]]]) -> int:
    counts = Counter(
        c
        for entries in grouped.values()
        for e in entries
        if e[2] is not None and e[3] is not None and (c := _recovered_count(e[3], e[2]))
    )
    return counts.most_common(1)[0][0] if counts else 1
