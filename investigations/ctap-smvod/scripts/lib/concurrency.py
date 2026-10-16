"""Pure concurrent-playback maths: session intervals -> per-minute concurrency over one UTC day.

No file or network I/O. A session counts toward every UTC minute its [start, end] interval overlaps.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Iterable, Mapping, Sequence

MINUTES_PER_DAY = 1440
Interval = tuple[datetime, datetime]


def parse_ts(text: str) -> datetime:
    """Parses '2026-10-14 01:39:23.892 UTC', '2026-10-14 14:33:07.296' or '2026-10-14T18:33:15.267Z' as UTC."""
    cleaned = text.strip().removesuffix("UTC").removesuffix("Z").strip().replace("T", " ")
    if not cleaned:
        raise ValueError("empty timestamp")
    return datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)


def intervals_from_session_rows(rows: Iterable[Mapping[str, str]]) -> tuple[dict[str, Interval], int]:
    """Exact intervals keyed by sessionId from rows with both event_start and event_end; returns (intervals, rows_without_end)."""
    out: dict[str, Interval] = {}
    skipped = 0
    for r in rows:
        sid = (r.get("sessionId") or "").strip()
        start, end = (r.get("event_start") or "").strip(), (r.get("event_end") or "").strip()
        if not (start and end):
            skipped += 1
            continue
        if not sid:
            raise ValueError(f"row with event times {start}..{end} but blank sessionId")
        s, e = parse_ts(start), parse_ts(end)
        if e < s:
            raise ValueError(f"session {sid}: event_end {end} before event_start {start}")
        out.setdefault(sid, (s, e))
    return out, skipped


def debug_spans(rows: Iterable[Mapping[str, str]]) -> dict[str, Interval]:
    """First and last debug-event timestamp per sessionId (the last event is an estimated end, not a real stop)."""
    seen: dict[str, list[datetime]] = defaultdict(list)
    for r in rows:
        sid, ts = (r.get("sessionId") or "").strip(), (r.get("datetime") or "").strip()
        if not sid or not ts:
            raise ValueError("debug row with blank sessionId or datetime")
        seen[sid].append(parse_ts(ts))
    return {sid: (min(v), max(v)) for sid, v in seen.items()}


def merge_with_estimates(
    exact: Mapping[str, Interval], session_ids: Sequence[str], spans: Mapping[str, Interval]
) -> tuple[dict[str, Interval], int, int]:
    """Exact intervals plus debug-estimated ones for the other ``session_ids``; returns (intervals, estimated, unresolved)."""
    merged = dict(exact)
    estimated = unresolved = 0
    for sid in dict.fromkeys(session_ids):
        if sid in merged:
            continue
        if sid in spans:
            merged[sid] = spans[sid]
            estimated += 1
        else:
            unresolved += 1
    return merged, estimated, unresolved


def per_minute_concurrency(intervals: Iterable[Interval], day: date) -> list[int]:
    """Sessions overlapping each of the 1440 UTC minutes of ``day`` (intervals are clipped to the day)."""
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
    delta = [0] * (MINUTES_PER_DAY + 1)
    for s, e in intervals:
        first = max(0, int((s.timestamp() - midnight) // 60))
        last = min(MINUTES_PER_DAY - 1, int((e.timestamp() - midnight) // 60))
        if last < 0 or first > MINUTES_PER_DAY - 1:
            continue
        delta[first] += 1
        delta[last + 1] -= 1
    counts, running = [], 0
    for i in range(MINUTES_PER_DAY):
        running += delta[i]
        counts.append(running)
    return counts


def peak(counts: Sequence[int]) -> tuple[int, int]:
    """(peak concurrency, first minute-of-day it occurs)."""
    if not counts:
        raise ValueError("empty concurrency series")
    top = max(counts)
    return top, counts.index(top)


def minute_label(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"
