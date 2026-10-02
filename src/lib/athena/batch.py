"""Concurrent batch submission + cache-first Athena query execution (ALI-5).

Design notes (see `docs/plan/src-lib-migration/athena-lib-integration/stories.md` ALI-5 for the full spec):

- **DIP:** `BatchQueryRunner` never constructs an `AthenaClient` or calls `athena_client()` itself -- per ALI-4's
  audit finding, `athena_runner.aws_clients.AwsClientFactory` builds every client from one shared `boto3.Session`,
  which is not documented as safe to build clients from concurrently. Every `AthenaClient` this class uses is
  pre-built, sequentially, on the calling thread, before any worker thread starts.
- **Client exclusivity:** a `queue.SimpleQueue`-backed pool hands each worker task its own `AthenaClient` for the
  duration of one query and returns it when done, so no two concurrently-running tasks ever share one client
  instance (a single `AthenaAdapter` is not safe for concurrent use -- see its own module docstring). This also
  bounds the number of simultaneously in-flight Athena calls to `min(len(clients), run_config.max_concurrency)`
  regardless of how many clients are supplied.
- **Pool size:** reuses `athena_runner.config.RunConfig.max_concurrency` (confirmed by ALI-4 to be an
  already-reserved-but-unconsumed field) rather than inventing a second, independent concurrency knob.
- **FCID propagation:** `contextvars` do not cross a `ThreadPoolExecutor` boundary automatically. `run_batch`
  takes a fresh `contextvars.copy_context()` snapshot for each submitted worker task (a single `Context` cannot
  be entered by two threads at once) so `src.lib.logging.context`'s FCID filter still reports the correct value
  from inside worker threads.
- **Failure propagation (this task's own documented design choice):** one query's failure does not blank out the
  batch -- `run_batch` always finishes every query it can, then raises a single `AthenaBatchExecutionError`
  carrying both `partial_results` (every `caller_key` that succeeded) and `failures` (every `caller_key` that
  raised). Chosen over fail-fast-on-first-error because partial results are usually still useful to an
  investigation workflow, and over silently dropping failed keys because that would hide a real query error as
  if it were just "no rows." Propagated exceptions are always this module's own `AthenaAdapterError` hierarchy.
"""
from __future__ import annotations

import contextvars
import logging
import queue
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from athena_runner.config import RunConfig

from src.lib.athena.cache import QueryResultCache, fingerprint_query
from src.lib.athena.exceptions import AthenaAdapterError, AthenaBatchExecutionError, AthenaQueryExecutionError
from src.lib.athena.protocols import AthenaClient, QueryResult
from src.lib.logging.context import FcidLogFilter

logger = logging.getLogger(__name__)
logger.addFilter(FcidLogFilter())


class BatchQueryRunner:
    """Runs a small batch of independent queries concurrently, cache-first.

    `clients` and `cache` are always constructor-injected, pre-built collaborators (DIP) -- this class never
    builds either one internally.
    """

    def __init__(self, clients: Sequence[AthenaClient], cache: QueryResultCache, run_config: RunConfig) -> None:
        if not clients or cache is None or run_config is None:
            raise ValueError("BatchQueryRunner requires non-empty clients, a cache, and a run_config -- none may be omitted.")
        self._cache = cache
        self._pool_size = max(1, min(len(clients), run_config.max_concurrency))
        self._client_pool: queue.SimpleQueue[AthenaClient] = queue.SimpleQueue()
        for client in clients:
            self._client_pool.put(client)

    def run_batch(self, queries: Sequence[tuple[str, str, Mapping[str, str]]]) -> dict[str, QueryResult]:
        """Runs every `(caller_key, sql, params)` tuple, cache-first, bounded by this runner's client pool.

        Returns a dict keyed by `caller_key` (not submission/completion order). Raises `AthenaBatchExecutionError`
        if any query failed -- see module docstring for why partial results are still attached to that exception
        rather than raised bare or silently dropped.
        """
        if not queries:
            return {}

        caller_keys = [caller_key for caller_key, _, _ in queries]
        if len(set(caller_keys)) != len(caller_keys):
            duplicates = sorted({key for key in caller_keys if caller_keys.count(key) > 1})
            raise ValueError(f"run_batch received duplicate caller_key(s), which is not supported: {duplicates}")

        results: dict[str, QueryResult] = {}
        failures: dict[str, Exception] = {}

        with ThreadPoolExecutor(max_workers=self._pool_size) as pool:
            # Each submitted task gets its own `copy_context()` snapshot (same bound values, e.g. FCID) --
            # a single `Context` object cannot be entered by more than one thread at once (`contextvars`
            # raises `RuntimeError` on re-entry), so one shared context cannot be reused across concurrent tasks.
            futures = [
                pool.submit(contextvars.copy_context().run, self._run_one, caller_key, sql, params)
                for caller_key, sql, params in queries
            ]
            for future in as_completed(futures):
                caller_key, result, error = future.result()
                if error is not None:
                    failures[caller_key] = error
                else:
                    assert result is not None  # invariant: error is None iff result is not None (see _run_one)
                    results[caller_key] = result

        if failures:
            raise AthenaBatchExecutionError(partial_results=results, failures=failures)
        return results

    def _run_one(
        self, caller_key: str, sql: str, params: Mapping[str, str]
    ) -> tuple[str, QueryResult | None, Exception | None]:
        client = self._client_pool.get()
        try:
            fingerprint = fingerprint_query(sql, params)
            cached = self._cache.get(fingerprint)
            if cached is not None:
                logger.info("cache hit for batch query %s", caller_key)
                return caller_key, cached, None
            logger.info("submitting batch query %s", caller_key)
            execution_id = client.start_query(sql, params)
            status = client.poll_status(execution_id)
            result = client.fetch_results(execution_id)
            # `AthenaClient` is a Protocol, not just `AthenaAdapter` -- a conforming implementation is not
            # guaranteed to raise on a non-success terminal state the way `AthenaAdapter.start_query` does
            # (see its own docstring). A silently-cached/returned "FAILED"/"CANCELLED" result would be exactly
            # the "error hidden as no rows" outcome this module's docstring says it prevents, so both the
            # polled status and the result's own `state` must be checked here before it is ever cached or
            # treated as a success.
            if status != "SUCCEEDED" or result.state != "SUCCEEDED":
                raise AthenaQueryExecutionError(
                    f"batch query {caller_key!r} did not succeed (poll_status={status!r}, result.state={result.state!r})"
                )
            self._cache.put(fingerprint, result)
            return caller_key, result, None
        except AthenaAdapterError as exc:
            logger.error("batch query %s failed: %s", caller_key, exc)
            return caller_key, None, exc
        except Exception as exc:  # noqa: BLE001 - deliberately broad: module docstring promises every
            # propagated exception is this module's own AthenaAdapterError hierarchy, and every query in the
            # batch must be allowed to finish regardless of what any single one raises (see module docstring).
            logger.error("batch query %s raised an unexpected error: %s", caller_key, exc, exc_info=True)
            wrapped = AthenaAdapterError(f"batch query {caller_key!r} raised an unexpected error: {exc}")
            wrapped.__cause__ = exc
            return caller_key, None, wrapped
        finally:
            self._client_pool.put(client)
