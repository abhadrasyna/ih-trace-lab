"""Tests for `src.lib.athena.progressive` -- fake `AthenaClient`/`ScopeSequence`/`SufficiencyCheck` only."""
from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.lib.athena.cache import InMemoryTtlCache
from src.lib.athena.exceptions import AthenaQueryExecutionError
from src.lib.athena.progressive import ProgressiveQueryRunner
from src.lib.athena.protocols import QueryResult


class _FakeClient:
    """Records every `(sql, scope)` it was asked to run."""

    def __init__(self, fail_on_call: int | None = None) -> None:
        self.calls: list[Mapping[str, str]] = []
        self._fail_on_call = fail_on_call

    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        self.calls.append(params)
        call_number = len(self.calls)
        if self._fail_on_call is not None and call_number == self._fail_on_call:
            raise AthenaQueryExecutionError(f"simulated failure on call {call_number}")
        return f"exec-{call_number}"

    def poll_status(self, execution_id: str) -> str:
        return "SUCCEEDED"

    def fetch_results(self, execution_id: str) -> QueryResult:
        call_number = int(execution_id.removeprefix("exec-"))
        rows = [{"call": str(call_number), "row": str(i)} for i in range(call_number)]
        return QueryResult(query_execution_id=execution_id, rows=rows, state="SUCCEEDED")


class _FiniteScopeSequence:
    """Widens through `scopes` in order, then returns `None`."""

    def __init__(self, scopes: list[Mapping[str, str]]) -> None:
        self._scopes = scopes
        self.widen_calls = 0

    def widen(self, previous: Mapping[str, str] | None) -> Mapping[str, str] | None:
        self.widen_calls += 1
        index = self.widen_calls - 1
        if index >= len(self._scopes):
            return None
        return self._scopes[index]


class _AlwaysSufficient:
    def is_sufficient(self, rows: list[dict[str, str]]) -> bool:
        return True


class _NeverSufficient:
    def is_sufficient(self, rows: list[dict[str, str]]) -> bool:
        return False


class _SufficientAfterNRows:
    def __init__(self, min_rows: int) -> None:
        self._min_rows = min_rows

    def is_sufficient(self, rows: list[dict[str, str]]) -> bool:
        return len(rows) >= self._min_rows


def test_runner_construction_requires_collaborators() -> None:
    with pytest.raises(TypeError):
        # Deliberately missing all 3 required constructor args (client/scopes/check) -- this epic's DIP-pair
        # convention (see test_protocol_conformance.py) asserts zero-arg construction raises TypeError.
        ProgressiveQueryRunner()  # type: ignore[call-arg]


def test_runner_stops_at_first_sufficient_scope() -> None:
    client = _FakeClient()
    scopes = _FiniteScopeSequence([{"days": "1"}, {"days": "7"}, {"days": "30"}])
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_AlwaysSufficient())

    runner.run("SELECT 1")

    assert scopes.widen_calls == 1
    assert len(client.calls) == 1


def test_runner_combines_rows_across_all_scopes_run() -> None:
    client = _FakeClient()
    scopes = _FiniteScopeSequence([{"days": "1"}, {"days": "7"}])
    # SufficiencyCheck only ever sees the *current* scope's own rows (per the spec's run() contract), not rows
    # accumulated across scopes -- scope 1 yields 1 row (insufficient), scope 2 yields 2 rows (sufficient),
    # so widening genuinely stops because of the check, not because scopes were exhausted.
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_SufficientAfterNRows(min_rows=2))

    result = runner.run("SELECT 1")

    assert len(client.calls) == 2
    assert len(result.rows) == 3  # 1 row from scope 1 + 2 rows from scope 2, both kept -- not just the last scope's
    assert result.rows[0]["call"] == "1"
    assert result.rows[1]["call"] == "2"
    assert result.rows[2]["call"] == "2"


def test_runner_stops_when_widen_returns_none() -> None:
    client = _FakeClient()
    scopes = _FiniteScopeSequence([{"days": "1"}, {"days": "7"}])  # exhausts after 2 scopes
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_NeverSufficient())

    runner.run("SELECT 1")

    assert len(client.calls) == 2  # no 3rd query attempt, even though check never returned True
    assert scopes.widen_calls == 3  # the 3rd widen() call is the one that returned None and stopped the loop


class _InfiniteScopeSequence:
    """Always returns the same scope -- a misbehaving `ScopeSequence` that never exhausts."""

    def widen(self, previous: Mapping[str, str] | None) -> Mapping[str, str] | None:
        return {"days": "1"}


def test_runner_stops_at_max_rounds_backstop_instead_of_looping_forever() -> None:
    client = _FakeClient()
    runner = ProgressiveQueryRunner(
        client=client, scopes=_InfiniteScopeSequence(), check=_NeverSufficient(), max_rounds=5
    )

    with pytest.raises(AthenaQueryExecutionError, match="max_rounds"):
        runner.run("SELECT 1")

    assert len(client.calls) == 5  # bounded by max_rounds, not an unbounded number of (billed) Athena calls


def test_runner_exhausting_exactly_at_max_rounds_does_not_raise() -> None:
    # A genuinely exhausted ScopeSequence that happens to have exactly max_rounds scopes is not a misbehaving
    # collaborator -- max_rounds must only fire on a round that *wasn't* stopped by a real widen() -> None.
    client = _FakeClient()
    scopes = _FiniteScopeSequence([{"days": str(i)} for i in range(5)])
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_NeverSufficient(), max_rounds=5)

    result = runner.run("SELECT 1")

    assert len(client.calls) == 5
    assert len(result.rows) == sum(range(1, 6))  # rows from all 5 scopes combined


def test_runner_rejects_non_positive_max_rounds() -> None:
    with pytest.raises(ValueError, match="positive"):
        ProgressiveQueryRunner(
            client=_FakeClient(), scopes=_InfiniteScopeSequence(), check=_NeverSufficient(), max_rounds=0
        )


def test_runner_propagates_real_query_failure_immediately() -> None:
    client = _FakeClient(fail_on_call=2)
    scopes = _FiniteScopeSequence([{"days": "1"}, {"days": "7"}, {"days": "30"}])
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_NeverSufficient())

    with pytest.raises(AthenaQueryExecutionError, match="simulated failure on call 2"):
        runner.run("SELECT 1")

    assert len(client.calls) == 2  # the failure on the 2nd scope was not silently swallowed or fallen back from


def test_runner_consults_cache_before_rerunning_a_scope() -> None:
    client = _FakeClient()
    cache = InMemoryTtlCache(ttl_seconds=60)
    scope = {"days": "1"}
    scopes = _FiniteScopeSequence([scope])
    runner = ProgressiveQueryRunner(client=client, scopes=scopes, check=_AlwaysSufficient(), cache=cache)

    runner.run("SELECT 1")
    assert len(client.calls) == 1

    # second runner, same scope + cache -- the scope's AthenaClient.start_query must never be called again.
    second_client = _FakeClient()
    second_runner = ProgressiveQueryRunner(
        client=second_client, scopes=_FiniteScopeSequence([scope]), check=_AlwaysSufficient(), cache=cache
    )
    second_runner.run("SELECT 1")

    assert len(second_client.calls) == 0
