"""Playback success rule."""
from __future__ import annotations

SUCCESS_OUTCOME = "DESTROY"


def is_success(playback_outcome: str | None) -> bool:
    """True only for DESTROY; EBVS, INCOMPLETE_NO_DESTROY, blank and None are not success."""
    return (playback_outcome or "").strip() == SUCCESS_OUTCOME
