"""`src/lib/athena`'s own exception hierarchy.

`AthenaAdapter` (see `adapter.py`) always raises one of these, never a raw
`athena_runner.exceptions.*` type — this keeps the submodule swappable
without every consumer's `except` clause needing to change if the
delegation target is ever replaced.
"""
from __future__ import annotations


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
