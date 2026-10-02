"""Tests for `src.lib.athena.adapter` -- mocked `athena_runner` collaborators only, no live AWS/network calls."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
from athena_runner import config as athena_runner_config
from athena_runner import exceptions as runner_exceptions
from athena_runner.query_executor import QueryResult as RunnerQueryResult
from botocore.exceptions import ClientError

from src.lib.athena.adapter import AthenaAdapter
from src.lib.athena.exceptions import (
    AthenaAuthError,
    AthenaQueryExecutionError,
    AthenaQueryTimeoutError,
    AthenaResultDownloadError,
)


def _throttling_error(operation_name: str = "StartQueryExecution") -> ClientError:
    return ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, operation_name)


def _non_throttling_error() -> ClientError:
    return ClientError({"Error": {"Code": "InvalidRequestException", "Message": "bad sql"}}, "StartQueryExecution")


class _FakeExecutor:
    """Records calls; returns/raises each entry of `outcomes` in order, one per `run()` call."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[tuple[str, str]] = []

    def run(self, sql: str, database: str) -> RunnerQueryResult:
        self.calls.append((sql, database))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _FakeDownloader:
    """Writes a tiny CSV to `destination_path`, or raises each entry of `outcomes` in order, one per `download()` call."""

    def __init__(self, outcomes: list[object] | None = None) -> None:
        self._outcomes = list(outcomes) if outcomes is not None else None
        self.calls: list[tuple[str, str]] = []

    def download(self, output_location: str, destination_path: str) -> None:
        self.calls.append((output_location, destination_path))
        if self._outcomes is not None:
            outcome = self._outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
        Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
        with open(destination_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["col"])
            writer.writerow(["value"])


def _make_config(tmp_path: Path) -> athena_runner_config.RunConfig:
    return athena_runner_config.RunConfig(
        profile="test-profile",
        workgroup="test-workgroup",
        output_location="s3://bucket/output/",
        output_dir=str(tmp_path),
    )


def _success_result(execution_id: str = "exec-1") -> RunnerQueryResult:
    return RunnerQueryResult(
        query_execution_id=execution_id,
        output_location="s3://bucket/output/result.csv",
        data_scanned_bytes=1024,
        engine_execution_ms=500,
    )


def test_adapter_delegates_start_query(tmp_path: Path) -> None:
    executor = _FakeExecutor([_success_result("exec-1")])
    downloader = _FakeDownloader()
    adapter = AthenaAdapter(executor, downloader, _make_config(tmp_path), database="test_db")

    execution_id = adapter.start_query("SELECT * FROM t WHERE day = $day", {"day": "2026-10-02"})

    assert execution_id == "exec-1"
    # params are quoted as SQL string literals, never substituted raw (avoids unquoted-arithmetic misparsing).
    assert executor.calls == [("SELECT * FROM t WHERE day = '2026-10-02'", "test_db")]
    result = adapter.fetch_results(execution_id)
    assert result.query_execution_id == "exec-1"
    assert result.state == "SUCCEEDED"
    assert result.rows == [{"col": "value"}]
    assert adapter.poll_status(execution_id) == "SUCCEEDED"


def test_adapter_quotes_and_escapes_param_values(tmp_path: Path) -> None:
    """A value containing a single quote must not break out of its SQL string literal."""
    executor = _FakeExecutor([_success_result("exec-1")])
    adapter = AthenaAdapter(executor, _FakeDownloader(), _make_config(tmp_path), database="test_db")

    adapter.start_query("SELECT * FROM t WHERE name = $name", {"name": "O'Brien"})

    assert executor.calls == [("SELECT * FROM t WHERE name = 'O''Brien'", "test_db")]


def test_adapter_raises_on_missing_template_param(tmp_path: Path) -> None:
    executor = _FakeExecutor([])
    adapter = AthenaAdapter(executor, _FakeDownloader(), _make_config(tmp_path), database="test_db")

    with pytest.raises(ValueError):
        adapter.start_query("SELECT * FROM t WHERE day = $day", {})

    assert executor.calls == []  # never reached the executor -- fails before any AWS-shaped call


def test_adapter_constructor_requires_injection(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    with pytest.raises(ValueError):
        AthenaAdapter(None, _FakeDownloader(), config, database="test_db")
    with pytest.raises(ValueError):
        AthenaAdapter(_FakeExecutor([]), None, config, database="test_db")
    with pytest.raises(ValueError):
        AthenaAdapter(_FakeExecutor([]), _FakeDownloader(), None, database="test_db")
    with pytest.raises(ValueError):
        AthenaAdapter(_FakeExecutor([]), _FakeDownloader(), config, database="")


def test_adapter_wraps_runner_exception(tmp_path: Path) -> None:
    executor = _FakeExecutor([runner_exceptions.QueryExecutionError("FAILED: bad sql")])
    adapter = AthenaAdapter(executor, _FakeDownloader(), _make_config(tmp_path), database="test_db")

    with pytest.raises(AthenaQueryExecutionError):
        adapter.start_query("SELECT 1", {})


def test_adapter_wraps_timeout_and_auth_errors(tmp_path: Path) -> None:
    config = _make_config(tmp_path)

    timeout_adapter = AthenaAdapter(
        _FakeExecutor([runner_exceptions.QueryTimeoutError("still RUNNING")]), _FakeDownloader(), config, database="test_db"
    )
    with pytest.raises(AthenaQueryTimeoutError):
        timeout_adapter.start_query("SELECT 1", {})

    auth_adapter = AthenaAdapter(
        _FakeExecutor([runner_exceptions.SsoLoginError("sso expired")]), _FakeDownloader(), config, database="test_db"
    )
    with pytest.raises(AthenaAuthError):
        auth_adapter.start_query("SELECT 1", {})


def test_adapter_retries_start_throttling_then_succeeds(tmp_path: Path) -> None:
    """Throttling raised by the StartQueryExecution call itself is safe to retry -- no query has started yet."""
    executor = _FakeExecutor(
        [_throttling_error("StartQueryExecution"), _throttling_error("StartQueryExecution"), _success_result("exec-1")]
    )
    downloader = _FakeDownloader()
    sleeps: list[float] = []
    adapter = AthenaAdapter(
        executor, downloader, _make_config(tmp_path), database="test_db", sleep_fn=sleeps.append, base_delay_seconds=0.01
    )

    execution_id = adapter.start_query("SELECT 1", {})

    assert execution_id == "exec-1"
    assert len(executor.calls) == 3
    assert len(sleeps) == 2  # one sleep per retried throttling attempt, none on the final success


def test_adapter_does_not_retry_poll_phase_throttling(tmp_path: Path) -> None:
    """Throttling raised by GetQueryExecution (mid-poll) means a query may already be running -- never auto-retried."""
    executor = _FakeExecutor([_throttling_error("GetQueryExecution"), _success_result("exec-1")])
    sleeps: list[float] = []
    adapter = AthenaAdapter(
        executor, _FakeDownloader(), _make_config(tmp_path), database="test_db", sleep_fn=sleeps.append
    )

    with pytest.raises(AthenaQueryExecutionError):
        adapter.start_query("SELECT 1", {})

    assert len(executor.calls) == 1  # no retry -- re-running risks a duplicate, billed query
    assert sleeps == []


def test_adapter_does_not_retry_non_throttling_errors(tmp_path: Path) -> None:
    executor = _FakeExecutor([_non_throttling_error(), _success_result("exec-1")])
    sleeps: list[float] = []
    adapter = AthenaAdapter(
        executor, _FakeDownloader(), _make_config(tmp_path), database="test_db", sleep_fn=sleeps.append
    )

    with pytest.raises(AthenaQueryExecutionError) as exc_info:
        adapter.start_query("SELECT 1", {})

    assert isinstance(exc_info.value.__cause__, ClientError)  # original botocore error never leaks to the caller directly
    assert len(executor.calls) == 1  # no retry attempted
    assert sleeps == []


def test_adapter_wraps_download_client_error(tmp_path: Path) -> None:
    downloader = _FakeDownloader(outcomes=[_non_throttling_error()])
    adapter = AthenaAdapter(_FakeExecutor([_success_result("exec-1")]), downloader, _make_config(tmp_path), database="test_db")

    with pytest.raises(AthenaResultDownloadError):
        adapter.start_query("SELECT 1", {})


def test_adapter_retries_download_throttling_then_succeeds(tmp_path: Path) -> None:
    downloader = _FakeDownloader(outcomes=[_throttling_error("GetObject"), None])
    sleeps: list[float] = []
    adapter = AthenaAdapter(
        _FakeExecutor([_success_result("exec-1")]),
        downloader,
        _make_config(tmp_path),
        database="test_db",
        sleep_fn=sleeps.append,
        base_delay_seconds=0.01,
    )

    execution_id = adapter.start_query("SELECT 1", {})

    assert execution_id == "exec-1"
    assert len(downloader.calls) == 2
    assert len(sleeps) == 1


def test_fetch_results_before_start_query_raises(tmp_path: Path) -> None:
    adapter = AthenaAdapter(_FakeExecutor([]), _FakeDownloader(), _make_config(tmp_path), database="test_db")

    with pytest.raises(AthenaQueryExecutionError):
        adapter.fetch_results("never-started")
