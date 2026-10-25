"""Pure check: which ``playback_outcome`` do sessions of one funnel cell (license outcome x error) carry?

No file or network I/O. ``drm_only`` sessions are not in the CTAP/SMVOD merge, so they have no outcome.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from lib.drm_funnel import NO_ERROR, SOURCE_DRM_ONLY, ClassifiedSession

NO_MERGE_OUTCOME = "(drm_only: not in merge)"
BLANK_OUTCOME = "(blank)"


def outcome_map(
    rows: Iterable[Mapping[str, str]], columns: Sequence[str] = ("playback_outcome",)
) -> dict[str, str]:
    """``sessionId -> " | "``-joined values of ``columns``.

    Duplicate merge rows must agree per column (a blank defers to a non-blank); a conflict raises.
    """
    merged: dict[str, list[str]] = {}
    for r in rows:
        sid = r["sessionId"].strip()
        if not sid:
            continue
        values = merged.setdefault(sid, [""] * len(columns))
        for i, col in enumerate(columns):
            new = r[col].strip()
            if values[i] and new and values[i] != new:
                raise ValueError(f"session {sid}: conflicting {col} {values[i]!r} vs {new!r}")
            values[i] = new or values[i]
    return {sid: " | ".join(v or BLANK_OUTCOME for v in vals) for sid, vals in merged.items()}


def playback_outcome_of(session: ClassifiedSession, outcome_by_session: Mapping[str, str]) -> str:
    if session.source == SOURCE_DRM_ONLY:
        return NO_MERGE_OUTCOME
    return outcome_by_session.get(session.session_id, BLANK_OUTCOME)


def tabulate_playback_outcome(
    sessions: Sequence[ClassifiedSession],
    outcome_by_session: Mapping[str, str],
    license_outcome: str,
    error_code: str = NO_ERROR,
) -> Counter[str]:
    """Sessions per ``playback_outcome`` for one license outcome and one error code (``no_error`` = no error)."""
    counts: Counter[str] = Counter()
    for s in sessions:
        if s.license_outcome == license_outcome and (s.error_code or NO_ERROR) == error_code:
            counts[playback_outcome_of(s, outcome_by_session)] += 1
    return counts
