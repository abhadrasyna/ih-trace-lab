"""The chart error boundary: callers see ``ChartError`` only, never matplotlib or numpy exception types."""

from __future__ import annotations

from typing import Sequence


class ChartError(Exception):
    """Raised for invalid chart input or any failure while drawing."""


def require_series(xs: Sequence[object], ys: Sequence[object]) -> None:
    """Rejects empty or mismatched-length input before any drawing starts."""
    if len(xs) == 0 or len(ys) == 0:
        raise ChartError("chart input must not be empty")
    if len(xs) != len(ys):
        raise ChartError(f"length mismatch: {len(xs)} x values vs {len(ys)} y values")
