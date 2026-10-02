"""Progressive scope-widening Athena query runner (ALI-6).

Design notes (see `docs/plan/src-lib-migration/athena-lib-integration/stories.md` ALI-6 for the full spec):

- **Template Method:** the widen-check-combine loop shape is fixed in `ProgressiveQueryRunner.run` -- only
  "what counts as a wider scope" (`ScopeSequence`) and "what counts as sufficient" (`SufficiencyCheck`) vary
  per consumer, and both are constructor-injected `Protocol`s rather than a fixed enum of widening steps.
- **Iterator:** scopes are produced lazily, one `widen()` call at a time -- a consumer whose first (narrowest)
  scope already satisfies `SufficiencyCheck` never pays for computing or running any wider scope.
- **Validated like ALI-5:** each scope's `poll_status()`/`fetch_results()` result is checked for an actual
  `"SUCCEEDED"` state before its rows are trusted, for the same reason `batch.py` does -- `AthenaClient` is a
  `Protocol`, not just `AthenaAdapter`, and a conforming implementation is not guaranteed to raise on a
  non-success terminal state.
- **Failure propagation:** a real query failure (an `AthenaAdapterError`) is never caught-and-continued past --
  that would silently fall back to an earlier, possibly-insufficient scope's partial result and hide a real
  error as if it were just "not enough rows yet." Only `SufficiencyCheck.is_sufficient(...) is False` drives
  widening; an exception always propagates immediately.
- **Known limitation (documented, not silently invented):** combined rows across scopes are concatenated, not
  deduplicated, unless the caller's own `SufficiencyCheck`/consumer logic handles overlap -- this module does
  not invent a dedup key, since rows are untyped `dict[str, str]` with no guaranteed unique column.
- **`query_execution_id` on the combined result:** since one `QueryResult` can only carry a single
  `query_execution_id` field, the combined result reports the *last* scope's run actually executed (the one
  that was sufficient, or the final one tried before `widen()` returned `None`) -- earlier scopes' execution
  ids are not discarded information, they are simply not representable in this dataclass's single-id shape.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from src.lib.athena.cache import QueryResultCache, fingerprint_query
from src.lib.athena.exceptions import AthenaQueryExecutionError
from src.lib.athena.protocols import AthenaClient, QueryResult

logger = logging.getLogger(__name__)


@runtime_checkable
class ScopeSequence(Protocol):
    """Strategy seam for what "a wider scope" means to a given consumer (time window, tenant fan-out, etc.)."""

    def widen(self, previous: Mapping[str, str] | None) -> Mapping[str, str] | None:
        """Returns the next, wider scope's query params given `previous` (`None` on the first call), or `None`
        when there is no wider scope left to try."""
        ...


@runtime_checkable
class SufficiencyCheck(Protocol):
    """Strategy seam for what "enough rows" means to a given consumer."""

    def is_sufficient(self, rows: list[dict[str, str]]) -> bool:
        ...


class ProgressiveQueryRunner:
    """Runs `sql` against a narrow scope first, widening only if `SufficiencyCheck` says the result isn't enough.

    `client`, `scopes`, and `check` are always constructor-injected, pre-built collaborators (DIP) -- this class
    never builds any of them internally. `cache` is the one optional collaborator: when supplied, each scope's
    rerun is checked against it first (same `fingerprint_query` shape ALI-5's `BatchQueryRunner` uses) so
    retrying a scope a consumer has already paid for doesn't resubmit to Athena.

    `max_rounds` bounds the widen-check loop (default 50) -- a buggy `ScopeSequence` that returns the same
    scope forever, or one paired with a `SufficiencyCheck` that never returns `True`, would otherwise submit an
    unbounded number of (billed) Athena queries. `widen()` returning `None` is still the expected, normal way
    for the loop to stop; `max_rounds` is only a backstop against a misbehaving collaborator, surfaced as a
    distinct `AthenaQueryExecutionError` rather than a silent truncation of results.
    """

    def __init__(
        self,
        client: AthenaClient,
        scopes: ScopeSequence,
        check: SufficiencyCheck,
        cache: QueryResultCache | None = None,
        *,
        max_rounds: int = 50,
    ) -> None:
        if client is None or scopes is None or check is None:
            raise ValueError("ProgressiveQueryRunner requires a client, a scopes sequence, and a check -- none may be omitted.")
        if max_rounds <= 0:
            raise ValueError("ProgressiveQueryRunner requires a positive max_rounds.")
        self._client = client
        self._scopes = scopes
        self._check = check
        self._cache = cache
        self._max_rounds = max_rounds

    def run(self, sql: str) -> QueryResult:
        """Runs `sql` against progressively wider scopes until `SufficiencyCheck` is satisfied or scopes are
        exhausted, returning a `QueryResult` whose rows combine every scope actually run."""
        combined_rows: list[dict[str, str]] = []
        last_result: QueryResult | None = None
        previous_scope: Mapping[str, str] | None = None
        rounds_run = 0

        while True:
            scope = self._scopes.widen(previous_scope)
            if scope is None:
                # A genuinely exhausted ScopeSequence always stops this way, regardless of how many rounds
                # it took -- running exactly `max_rounds` real (non-exhausted) scopes is not itself a
                # misbehaving collaborator, so this path must be reachable even when rounds_run == max_rounds.
                break
            previous_scope = scope
            rounds_run += 1
            if rounds_run > self._max_rounds:
                raise AthenaQueryExecutionError(
                    f"ProgressiveQueryRunner.run: exceeded max_rounds={self._max_rounds} widen/check rounds "
                    "without SufficiencyCheck ever returning True or ScopeSequence.widen(...) ever returning "
                    "None -- this looks like a misbehaving ScopeSequence/SufficiencyCheck pair, not real "
                    "insufficient data."
                )

            result = self._run_one_scope(sql, scope)
            combined_rows.extend(result.rows)
            last_result = result

            if self._check.is_sufficient(result.rows):
                break

        if last_result is None:
            # `ScopeSequence.widen(None)` returned `None` immediately -- no scope was ever considered wide
            # enough to try even once. This is a consumer configuration error, not a normal "insufficient
            # rows" outcome, so it is surfaced distinctly rather than returning a fabricated empty result.
            raise AthenaQueryExecutionError("ProgressiveQueryRunner.run: ScopeSequence produced no scope to run (widen(None) returned None).")

        return QueryResult(query_execution_id=last_result.query_execution_id, rows=combined_rows, state="SUCCEEDED")

    def _run_one_scope(self, sql: str, scope: Mapping[str, str]) -> QueryResult:
        fingerprint = fingerprint_query(sql, scope)
        if self._cache is not None:
            cached = self._cache.get(fingerprint)
            if cached is not None:
                logger.info("cache hit for progressive scope %s", scope)
                return cached

        logger.info("running progressive scope %s", scope)
        execution_id = self._client.start_query(sql, scope)
        status = self._client.poll_status(execution_id)
        result = self._client.fetch_results(execution_id)
        if status != "SUCCEEDED" or result.state != "SUCCEEDED":
            raise AthenaQueryExecutionError(
                f"progressive scope {scope!r} did not succeed (poll_status={status!r}, result.state={result.state!r})"
            )

        if self._cache is not None:
            self._cache.put(fingerprint, result)
        return result
