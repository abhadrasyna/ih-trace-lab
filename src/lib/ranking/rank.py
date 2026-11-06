"""Rank rows by a count with stable, explicit tie-breaking."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any


def rank_by_count(rows: Iterable[dict], key: str | Callable[[dict], Any], *, top: int | None = None,
                  tie_breakers: Sequence[Callable[[Any], Any]] = ()) -> list[dict]:
    """Count rows per ``key`` and return ``{"rank", "key", "count"}`` dicts, highest count first.

    ``key`` is a column name or a function of the row; rows whose key is None are rejected loudly.
    Ties fall back to ``tie_breakers`` (functions of the key value, ascending), then to first-seen
    order, so the result is deterministic. ``top`` keeps the first N entries (None keeps all).
    """
    if top is not None and top < 0:
        raise ValueError(f"top must be >= 0, got {top}")
    getter = key if callable(key) else (lambda r, k=key: r.get(k))
    counts: dict[Any, int] = {}
    for row in rows:
        value = getter(row)
        if value is None:
            raise ValueError(f"row has no value for ranking key {key!r}: {row!r}")
        counts[value] = counts.get(value, 0) + 1
    if any(not callable(b) for b in tie_breakers):
        raise ValueError("tie_breakers must be callables of the key value")
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], *(b(kv[0]) for b in tie_breakers)))
    if top is not None:
        ordered = ordered[:top]
    return [{"rank": i, "key": k, "count": n} for i, (k, n) in enumerate(ordered, 1)]
