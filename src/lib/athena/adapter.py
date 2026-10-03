"""DIP-compliant adapter satisfying FCT-2's `AthenaClient` Protocol by delegating to the already-independent `athena_runner` submodule
(`vendor/athena-mcp-server`) rather than re-implementing its start/poll/download logic a fifth time.

Design notes (see `docs/plan/src-lib-migration/athena-lib-integration/stories.md` ALI-2 for the full spec this implements):

- `athena_runner.query_executor.AthenaQueryExecutor.run()` is the submodule's only public entry point and is blocking: it starts the
  query, polls until a terminal state, and either returns a result or raises. There is no public non-blocking "just start" or "just
  poll" method to delegate to separately (the real start/poll calls are private implementation details of `run()`). `AthenaAdapter`
  therefore performs the real work inside `start_query` (where `run()` is called), caches the terminal outcome keyed by Athena's own
  `query_execution_id`, and `poll_status`/`fetch_results` are cheap lookups against that cache rather than separate round trips -- the
  Protocol's three-method shape is preserved without inventing a fake async layer over a synchronous API.
- `params` are bound into `sql` as quoted-and-escaped SQL string literals via strict `string.Template.substitute` (raises on a
  missing key rather than silently leaving `$name` in the SQL, and never lets a param value be interpreted as unquoted SQL/arithmetic)
  -- this is mechanical parameter substitution (DB-API-cursor-style plumbing), not query-text authorship; the SQL text itself still
  comes entirely from the caller.
- Throttling-class `botocore.exceptions.ClientError` (`ThrottlingException`/`TooManyRequestsException`) is retried with exponential
  backoff + jitter **only when it is raised by the `StartQueryExecution` boto3 call** (i.e. before any query has actually started) --
  `athena_runner.run()` both starts and polls a query in one blocking call, so a throttling error raised mid-poll (`GetQueryExecution`)
  means a query is already running/billing; blindly retrying the whole call in that case would submit a second, duplicate query. Any
  other error -- including non-throttling `ClientError`, and throttling during polling -- propagates immediately, wrapped in this
  module's own exception hierarchy, never retried.
- Downloaded CSV files accumulate under `config.output_dir` with no automatic cleanup -- this adapter is a thin execution/translation
  layer, not a cache; a long-running caller is responsible for its own retention policy (a future consumer-side concern, not this
  module's).
"""
from __future__ import annotations

import csv
import logging
import random
import string
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from athena_runner import config as athena_runner_config
from athena_runner import exceptions as runner_exceptions
from botocore.exceptions import ClientError

from src.lib.athena.exceptions import (
    AthenaAuthError,
    AthenaQueryExecutionError,
    AthenaQueryTimeoutError,
    AthenaResultDownloadError,
)
from src.lib.athena.protocols import QueryResult

if TYPE_CHECKING:
    from athena_runner.query_executor import AthenaQueryExecutor
    from athena_runner.query_executor import QueryResult as RunnerQueryResult
    from athena_runner.result_downloader import ResultDownloader

_logger = logging.getLogger(__name__)

_THROTTLING_ERROR_CODES = frozenset({"ThrottlingException", "TooManyRequestsException"})
_START_QUERY_OPERATION = "StartQueryExecution"

_T = TypeVar("_T")


def _is_throttling_client_error(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code") in _THROTTLING_ERROR_CODES


def _is_retryable_start_throttling(exc: BaseException) -> bool:
    """True only when `exc` is a throttling `ClientError` raised by the `StartQueryExecution` call itself.

    Retrying is only safe before a query exists -- see module docstring. A throttling error from any other boto3
    operation (e.g. `GetQueryExecution` during polling) means a query may already be running; it is not retried here.
    """
    return _is_throttling_client_error(exc) and getattr(exc, "operation_name", None) == _START_QUERY_OPERATION


def _quote_sql_literal(value: str) -> str:
    """Quotes `value` as a single SQL string literal, doubling any embedded single quotes."""
    return "'" + value.replace("'", "''") + "'"


class AthenaAdapter:
    """`AthenaClient` Protocol implementation delegating to constructor-injected `athena_runner` collaborators.

    Never constructs its own `boto3` client or `athena_runner` instance (DIP) -- `executor`, `downloader`, and `config` are always
    supplied by the caller.
    """

    def __init__(
        self,
        executor: AthenaQueryExecutor,
        downloader: ResultDownloader,
        config: athena_runner_config.RunConfig,
        database: str,
        *,
        base_delay_seconds: float = 1.0,
        max_retries: int = 5,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if executor is None or downloader is None or config is None:
            raise ValueError("AthenaAdapter requires executor, downloader, and config collaborators -- none may be omitted.")
        if not database:
            raise ValueError("AthenaAdapter requires a non-empty `database` to run queries against.")
        self._executor = executor
        self._downloader = downloader
        self._config = config
        self._database = database
        self._base_delay_seconds = base_delay_seconds
        self._max_retries = max_retries
        self._sleep_fn = sleep_fn
        self._results: dict[str, QueryResult] = {}

    def start_query(self, sql: str, params: Mapping[str, str]) -> str:
        """Binds `params` into `sql` as quoted literals, runs it to completion, and returns Athena's own execution id.

        Blocking, because `athena_runner`'s own `run()` is blocking -- see module docstring.
        """
        bound_sql = self._bind_params(sql, params)
        runner_result = self._run_with_retry(bound_sql)
        self._results[runner_result.query_execution_id] = self._download_and_translate(runner_result)
        return runner_result.query_execution_id

    def poll_status(self, execution_id: str) -> str:
        """Returns the cached terminal state for `execution_id` (always `SUCCEEDED` -- `start_query` raises on any other outcome)."""
        return self._require_cached(execution_id).state

    def fetch_results(self, execution_id: str) -> QueryResult:
        """Returns the cached, already-downloaded `QueryResult` for `execution_id`."""
        return self._require_cached(execution_id)

    def _require_cached(self, execution_id: str) -> QueryResult:
        try:
            return self._results[execution_id]
        except KeyError as exc:
            raise AthenaQueryExecutionError(
                f"Unknown execution id {execution_id!r} -- start_query must be called first."
            ) from exc

    @staticmethod
    def _bind_params(sql: str, params: Mapping[str, str]) -> str:
        quoted = {key: _quote_sql_literal(value) for key, value in params.items()}
        try:
            return string.Template(sql).substitute(quoted)
        except KeyError as exc:
            raise ValueError(f"SQL template references a parameter not present in params={sorted(params)}: {exc}") from exc

    def _run_with_retry(self, sql: str) -> RunnerQueryResult:
        attempt = 0
        while True:
            try:
                return self._executor.run(sql, self._database)
            except runner_exceptions.QueryTimeoutError as exc:
                raise AthenaQueryTimeoutError(str(exc)) from exc
            except runner_exceptions.SsoLoginError as exc:
                raise AthenaAuthError(str(exc)) from exc
            except runner_exceptions.AthenaRunnerError as exc:
                raise AthenaQueryExecutionError(str(exc)) from exc
            except ClientError as exc:
                if not _is_retryable_start_throttling(exc) or attempt >= self._max_retries:
                    raise AthenaQueryExecutionError(f"Athena/boto3 client error: {exc}") from exc
                self._sleep_backoff(attempt)
                attempt += 1

    def _download_and_translate(self, runner_result: RunnerQueryResult) -> QueryResult:
        csv_path = str(Path(self._config.output_dir) / f"{runner_result.query_execution_id}.csv")
        self._download_with_retry(runner_result.output_location, csv_path)
        rows = self._read_rows(csv_path)
        return QueryResult(query_execution_id=runner_result.query_execution_id, rows=rows, state="SUCCEEDED")

    def _download_with_retry(self, output_location: str, csv_path: str) -> None:
        attempt = 0
        while True:
            try:
                self._downloader.download(output_location, csv_path)
                return
            except ClientError as exc:
                if not _is_throttling_client_error(exc) or attempt >= self._max_retries:
                    raise AthenaResultDownloadError(f"Failed to download Athena result: {exc}") from exc
                self._sleep_backoff(attempt)
                attempt += 1
            except OSError as exc:
                raise AthenaResultDownloadError(f"Failed to write downloaded CSV to {csv_path}: {exc}") from exc

    def _read_rows(self, csv_path: str) -> list[dict[str, str]]:
        try:
            with open(csv_path, newline="", encoding="utf-8") as csv_file:
                return list(csv.DictReader(csv_file))
        except OSError as exc:
            raise AthenaResultDownloadError(f"Failed to read downloaded CSV {csv_path}: {exc}") from exc

    def _sleep_backoff(self, attempt: int) -> None:
        delay = self._base_delay_seconds * (2**attempt) + random.uniform(0, self._base_delay_seconds)
        _logger.warning("Throttled starting an Athena query (attempt %s/%s); retrying in %.2fs", attempt + 1, self._max_retries, delay)
        self._sleep_fn(delay)
