"""Helpers for logging only an explicit, safe subset of parameters."""

from __future__ import annotations


def redact_params(params: dict[str, object], allow_keys: set[str]) -> dict[str, object]:
    """Return a copy of ``params`` with non-allow-listed values masked.

    Args:
        params: Parameters that may be included in a log line.
        allow_keys: Keys whose values are safe to log verbatim.

    Raises:
        ValueError: If ``allow_keys`` is empty.
    """
    if not allow_keys:
        raise ValueError("allow_keys must not be empty")
    return {key: value if key in allow_keys else "***" for key, value in params.items()}
