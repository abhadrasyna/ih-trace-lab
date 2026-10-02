"""Swappable TTL result cache for Athena query results (ALI-5).

`QueryResultCache` is kept as a `Protocol` (Strategy), not hardcoded to one storage backend, so a future
consumer can swap in a persistent cache (e.g. file- or Redis-backed) without `BatchQueryRunner` changing.
"""
from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable, Mapping
from time import monotonic
from typing import Protocol, runtime_checkable

from src.lib.athena.protocols import QueryResult


@runtime_checkable
class QueryResultCache(Protocol):
    """Strategy seam for `BatchQueryRunner`'s cache-first query flow."""

    def get(self, fingerprint: str) -> QueryResult | None:
        ...

    def put(self, fingerprint: str, result: QueryResult) -> None:
        ...


def fingerprint_query(sql: str, params: Mapping[str, str]) -> str:
    """Hashes `(sql, sorted(params))` so two calls with the same SQL + params collide regardless of dict order."""
    canonical = repr((sql, tuple(sorted(params.items()))))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class InMemoryTtlCache:
    """In-process `QueryResultCache` evicting entries older than `ttl_seconds`.

    `ttl_seconds` is a required constructor argument (no silent default), matching this epic's DIP-pair
    convention (see `tests/lib/athena/test_protocol_conformance.py`'s zero-arg-`TypeError` tests for ALI-2/3).
    """

    def __init__(self, ttl_seconds: int, *, clock: Callable[[], float] = monotonic) -> None:
        if ttl_seconds <= 0:
            raise ValueError("InMemoryTtlCache requires a positive ttl_seconds.")
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, tuple[QueryResult, float]] = {}
        self._lock = threading.Lock()

    def get(self, fingerprint: str) -> QueryResult | None:
        with self._lock:
            entry = self._entries.get(fingerprint)
            if entry is None:
                return None
            result, inserted_at = entry
            if self._clock() - inserted_at > self._ttl_seconds:
                # `.pop(..., None)` (not `del`) -- two threads can race to expire the same fingerprint, and a
                # bare `del` would raise `KeyError` on the second one instead of resolving to a plain cache miss.
                self._entries.pop(fingerprint, None)
                return None
            return result

    def put(self, fingerprint: str, result: QueryResult) -> None:
        with self._lock:
            now = self._clock()
            # Opportunistically evict every expired entry on write, not just the one being looked up on read --
            # otherwise a result for a one-off fingerprint that's never looked up again stays in `_entries` for
            # the life of the process (unbounded memory growth).
            expired = [key for key, (_, inserted_at) in self._entries.items() if now - inserted_at > self._ttl_seconds]
            for key in expired:
                del self._entries[key]
            self._entries[fingerprint] = (result, now)
