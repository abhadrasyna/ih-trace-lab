"""Pure check: which ``playback_outcome`` do sessions of one funnel cell (license outcome x error) carry?

No file or network I/O. ``drm_only`` sessions are not in the CTAP/SMVOD merge, so they have no outcome.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from lib.drm_funnel import NO_ERROR, SOURCE_DRM_ONLY, ClassifiedSession

NO_MERGE_OUTCOME = "(drm_only: not in merge)"
BLANK_OUTCOME = "(blank)"


def outcome_map(rows: Iterable[Mapping[str, str]]) -> dict[str, str]:
    """``sessionId -> playback_outcome``; duplicate merge rows must agree (a blank defers to a non-blank)."""
    out: dict[str, str] = {}
    for r in rows:
        sid, outcome = r["sessionId"].strip(), r["playback_outcome"].strip()
        if not sid:
            continue
        if out.get(sid) and outcome and out[sid] != outcome:
            raise ValueError(f"session {sid}: conflicting playback_outcome {out[sid]!r} vs {outcome!r}")
        out[sid] = outcome or out.get(sid, "")
    return out


def playback_outcome_of(session: ClassifiedSession, outcome_by_session: Mapping[str, str]) -> str:
    if session.source == SOURCE_DRM_ONLY:
        return NO_MERGE_OUTCOME
    return outcome_by_session.get(session.session_id, "").strip() or BLANK_OUTCOME


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
