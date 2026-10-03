"""Tests for `src.lib.athena.batch` + `src.lib.athena.cache` -- fake `AthenaClient`/clock only, no live AWS calls."""
from __future__ import annotations

import contextvars
import logging
import threading
import time
from collections.abc import Mapping

import pytest
from athena_runner.config import RunConfig

from src.lib.athena.batch import BatchQueryRunner
from src.lib.athena.cache import InMemoryTtlCache, fingerprint_query
from src.lib.athena.exceptions import (
    AthenaAdapterError,
    AthenaBatchExecutionError,
    AthenaQueryExecutionError,
)
from src.lib.athena.protocols import QueryResult
from src.lib.logging.context import bind_fcid, current_fcid


def _run_config(max_concurrency: int = 5) -> RunConfig:
    return RunConfig(
        profile="test-profile",
        workgroup="test-workgroup",
        output_location="s3://bucket/out",
        output_dir="/tmp/athena-batch-tests",
        max_concurrency=max_concurrency,
    )


class _FakeClient:
    """Records calls; one `_FakeClient` must never be used by two concurrent `run_batch` workers at once."""

    def __init__(
        self,
        high_water_mark: _HighWaterMark | None = None,
        fail_sql: str | None = None,
        raise_unexpected_for_sql: str | None = None,
    ) -> None:
        self.start_calls: list[str] = []
        self._high_water_mark = high_water_mark
        self._fail_sql = fail_sql
        self._raise_unexpected_for_sql = raise_unexpected_for_sql

    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        self.start_calls.append(sql)
        if self._high_water_mark is not None:
            self._high_water_mark.enter()
        try:
            if self._fail_sql is not None and sql == self._fail_sql:
                raise AthenaQueryExecutionError(f"simulated failure for {sql!r}")
            if self._raise_unexpected_for_sql is not None and sql == self._raise_unexpected_for_sql:
                raise RuntimeError(f"simulated non-adapter error for {sql!r}")
            return f"exec-{sql}"
        finally:
            if self._high_water_mark is not None:
                self._high_water_mark.exit()

    def poll_status(self, execution_id: str) -> str:
        return "SUCCEEDED"

    def fetch_results(self, execution_id: str) -> QueryResult:
        return QueryResult(query_execution_id=execution_id, rows=[{"col": execution_id}], state="SUCCEEDED")


class _HighWaterMark:
    """Thread-safe counter tracking the max number of concurrently-active `enter()`/`exit()` pairs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current = 0
        self.peak = 0

    def enter(self) -> None:
        with self._lock:
            self._current += 1
            self.peak = max(self.peak, self._current)
        time.sleep(0.02)  # widen the window so concurrent workers are likely to overlap

    def exit(self) -> None:
        with self._lock:
            self._current -= 1


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def test_batch_runner_construction_requires_collaborators() -> None:
    with pytest.raises(TypeError):
        # Deliberately missing all 3 required constructor args (clients/cache/run_config) -- this epic's
        # DIP-pair convention (see test_protocol_conformance.py) asserts zero-arg construction raises TypeError.
        BatchQueryRunner()  # type: ignore[call-arg]


def test_in_memory_ttl_cache_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError, match="positive"):
        InMemoryTtlCache(ttl_seconds=0)
    with pytest.raises(ValueError, match="positive"):
        InMemoryTtlCache(ttl_seconds=-1)


def test_run_batch_rejects_duplicate_caller_keys() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    runner = BatchQueryRunner(clients=[_FakeClient()], cache=cache, run_config=_run_config())

    with pytest.raises(ValueError, match="duplicate"):
        runner.run_batch([("dup", "SELECT 1", {}), ("dup", "SELECT 2", {})])


def test_fingerprint_is_stable_regardless_of_param_order() -> None:
    sql = "SELECT * FROM t WHERE a = $a AND b = $b"
    left = fingerprint_query(sql, {"a": "1", "b": "2"})
    right = fingerprint_query(sql, {"b": "2", "a": "1"})
    assert left == right


def test_ttl_cache_concurrent_expiry_does_not_raise() -> None:
    # Many threads racing to `get()` the exact same already-expired fingerprint must never raise KeyError --
    # `InMemoryTtlCache.get()` uses `.pop(fingerprint, None)`, not a bare `del`, for exactly this reason.
    clock = _FakeClock()
    cache = InMemoryTtlCache(ttl_seconds=10, clock=clock)
    cache.put("fp", QueryResult(query_execution_id="exec-1", rows=[], state="SUCCEEDED"))
    clock.advance(11)

    errors: list[BaseException] = []

    def _get() -> None:
        try:
            cache.get("fp")
        except BaseException as exc:  # noqa: BLE001 - intentionally broad: this test asserts *no* exception
            errors.append(exc)

    threads = [threading.Thread(target=_get) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors


def test_cache_hit_skips_athena_call() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    client = _FakeClient()
    runner = BatchQueryRunner(clients=[client], cache=cache, run_config=_run_config())

    sql: str = "SELECT 1"
    params: dict[str, str] = {}
    runner.run_batch([("k1", sql, params)])
    runner.run_batch([("k2", sql, params)])

    assert client.start_calls == [sql]  # second identical query is a cache hit, never calls start_query again


def test_ttl_cache_expires_entry() -> None:
    clock = _FakeClock()
    cache = InMemoryTtlCache(ttl_seconds=10, clock=clock)
    result = QueryResult(query_execution_id="exec-1", rows=[], state="SUCCEEDED")

    cache.put("fp", result)
    assert cache.get("fp") == result

    clock.advance(11)
    assert cache.get("fp") is None


def test_put_evicts_other_expired_entries_without_being_read_first() -> None:
    # A fingerprint that's cached once and never looked up again must not stay in `_entries` forever --
    # `put()` opportunistically sweeps expired entries on every write, not only on a matching `get()`.
    clock = _FakeClock()
    cache = InMemoryTtlCache(ttl_seconds=10, clock=clock)
    result = QueryResult(query_execution_id="exec-1", rows=[], state="SUCCEEDED")

    cache.put("one-off-fp", result)
    clock.advance(11)
    cache.put("other-fp", result)

    assert len(cache._entries) == 1
    assert "one-off-fp" not in cache._entries


def test_run_batch_preserves_caller_keys() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    client = _FakeClient()
    runner = BatchQueryRunner(clients=[client, _FakeClient()], cache=cache, run_config=_run_config())

    queries = [("key-b", "SELECT b", {}), ("key-a", "SELECT a", {}), ("key-c", "SELECT c", {})]  # type: list[tuple[str, str, dict[str, str]]]
    results = runner.run_batch(queries)

    assert set(results) == {"key-a", "key-b", "key-c"}
    assert results["key-a"].query_execution_id == "exec-SELECT a"
    assert results["key-b"].query_execution_id == "exec-SELECT b"
    assert results["key-c"].query_execution_id == "exec-SELECT c"


def test_one_query_failure_does_not_silently_blank_others() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    client = _FakeClient(fail_sql="SELECT bad")
    runner = BatchQueryRunner(clients=[client], cache=cache, run_config=_run_config(max_concurrency=1))

    with pytest.raises(AthenaBatchExecutionError) as exc_info:
        runner.run_batch([("good", "SELECT good", {}), ("bad", "SELECT bad", {})])

    error = exc_info.value
    assert "good" in error.partial_results
    good_result = error.partial_results["good"]
    assert isinstance(good_result, QueryResult)
    assert good_result.query_execution_id == "exec-SELECT good"
    assert "bad" in error.failures
    assert isinstance(error.failures["bad"], AthenaQueryExecutionError)


def test_non_adapter_exception_is_wrapped_and_does_not_abort_other_queries() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    client = _FakeClient(raise_unexpected_for_sql="SELECT boom")
    runner = BatchQueryRunner(clients=[client], cache=cache, run_config=_run_config(max_concurrency=1))

    with pytest.raises(AthenaBatchExecutionError) as exc_info:
        runner.run_batch([("good", "SELECT good", {}), ("boom", "SELECT boom", {})])

    error = exc_info.value
    assert "good" in error.partial_results
    assert "boom" in error.failures
    # the raw RuntimeError must never reach the caller directly -- it's always wrapped into this module's
    # own AthenaAdapterError hierarchy (see batch.py's module docstring).
    assert isinstance(error.failures["boom"], AthenaAdapterError)
    assert not isinstance(error.failures["boom"], RuntimeError)


def test_fcid_propagates_into_worker_threads() -> None:
    cache = InMemoryTtlCache(ttl_seconds=60)
    client = _FakeClient()
    runner = BatchQueryRunner(clients=[client], cache=cache, run_config=_run_config())

    observed_fcids: list[str | None] = []

    class _RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            observed_fcids.append(getattr(record, "fcid", None))

    batch_logger = logging.getLogger("src.lib.athena.batch")
    handler = _RecordingHandler()
    original_level = batch_logger.level
    batch_logger.addHandler(handler)
    batch_logger.setLevel(logging.INFO)

    def _bind_and_run() -> None:
        # Run inside a fresh `copy_context()` (not the test process's shared main context) so `bind_fcid`
        # cannot leak into whichever test runs next -- see `src.lib.logging.context`'s own non-reentrancy note.
        bind_fcid("test-fcid-12345")
        assert current_fcid() == "test-fcid-12345"
        runner.run_batch([("k1", "SELECT 1", {})])

    try:
        contextvars.copy_context().run(_bind_and_run)
    finally:
        batch_logger.removeHandler(handler)
        batch_logger.setLevel(original_level)

    assert observed_fcids, "expected at least one log record emitted from inside run_batch"
    assert all(fcid == "test-fcid-12345" for fcid in observed_fcids)


def test_pool_size_matches_run_config_max_concurrency() -> None:
    high_water_mark = _HighWaterMark()
    clients = [_FakeClient(high_water_mark=high_water_mark) for _ in range(5)]
    cache = InMemoryTtlCache(ttl_seconds=60)
    runner = BatchQueryRunner(clients=clients, cache=cache, run_config=_run_config(max_concurrency=2))

    queries = [(f"k{i}", f"SELECT {i}", {}) for i in range(5)]  # type: list[tuple[str, str, dict[str, str]]]
    results = runner.run_batch(queries)

    assert len(results) == 5
    # Asserts the pool actually reaches its bound (not just "never exceeds it") -- with 5 queries and a
    # pool size of 2, and `_HighWaterMark.enter()`'s sleep widening the overlap window, serial execution
    # (which would also satisfy a bare `<= 2`) cannot produce this result.
    assert high_water_mark.peak == 2
