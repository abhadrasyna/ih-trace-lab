"""Tests for src.lib.athena.protocols."""
from __future__ import annotations

from collections.abc import Mapping

from src.lib.athena.protocols import AthenaClient, QueryResult


class _ConformingAthenaClient:
    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        return "exec-123"

    def poll_status(self, execution_id: str) -> str:
        return "SUCCEEDED"

    def fetch_results(self, execution_id: str) -> QueryResult:
        return QueryResult(query_execution_id=execution_id, rows=[{"status": "ok"}], state="SUCCEEDED")


class _MissingFetchResults:
    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        return "exec-123"

    def poll_status(self, execution_id: str) -> str:
        return "SUCCEEDED"


def test_conforming_stub_satisfies_athena_client_protocol() -> None:
    assert isinstance(_ConformingAthenaClient(), AthenaClient)


def test_non_conforming_stub_does_not_satisfy_protocol() -> None:
    assert not isinstance(_MissingFetchResults(), AthenaClient)
