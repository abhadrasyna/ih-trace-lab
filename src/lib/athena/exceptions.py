"""`src/lib/athena`'s own exception hierarchy.

`AthenaAdapter` (see `adapter.py`) always raises one of these, never a raw
`athena_runner.exceptions.*` type — this keeps the submodule swappable
without every consumer's `except` clause needing to change if the
delegation target is ever replaced.
"""
from __future__ import annotations

from collections.abc import Mapping


class AthenaAdapterError(Exception):
    """Base class for all `src.lib.athena` errors."""


class AthenaQueryExecutionError(AthenaAdapterError):
    """Mirrors `athena_runner.exceptions.QueryExecutionError`."""


class AthenaQueryTimeoutError(AthenaAdapterError):
    """Mirrors `athena_runner.exceptions.QueryTimeoutError`."""


class AthenaAuthError(AthenaAdapterError):
    """Mirrors `athena_runner.exceptions.SsoLoginError`."""


class AthenaResultDownloadError(AthenaAdapterError):
    """Raised when downloading or reading a completed query's result CSV fails (S3 `ClientError` or local I/O error)."""


class AthenaBatchExecutionError(AthenaAdapterError):
    """Raised by `batch.BatchQueryRunner.run_batch` when one or more queries in a batch fail.

    Carries both `partial_results` (every `caller_key` that succeeded) and `failures` (every `caller_key` that raised,
    mapped to its own `AthenaAdapterError`) so a failure in one query never silently blanks out the others' results.
    """

    def __init__(self, partial_results: Mapping[str, object], failures: Mapping[str, Exception]) -> None:
        super().__init__(f"{len(failures)} of {len(partial_results) + len(failures)} batch queries failed: {sorted(failures)}")
        self.partial_results = partial_results
        self.failures = failures
