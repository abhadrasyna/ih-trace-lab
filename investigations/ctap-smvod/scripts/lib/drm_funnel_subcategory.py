"""Pure join of funnel sessions to the 3014/3015/3016 triage sub-category (no file or network I/O).

The rules live in ``classify_3016_subcategory``; rows are built by ``build_3016_subcategory_events.build_events``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from build_3016_subcategory_events import build_events
from lib.drm_funnel import NAMED_ERRORS


def _stub_row(session_id: str, code: str) -> dict:
    """A session whose first code came from the merge but has no flat event: the classifier's fallback applies."""
    return {"errorcode": code, "datetime": "", "householdId": "", "deviceId": "", "sessionId": session_id}


def subcategory_by_session(
    first_errors: Mapping[str, str],
    flat_rows: Sequence[dict],
    setup: dict,
    pos: dict,
    opco: str,
    date: str,
) -> dict[str, str]:
    """Sub-category per session whose first error code is 3014/3015/3016.

    ``first_errors`` maps sessionId to its first error code (the funnel's counting rule). The session's first flat
    event with that same code is classified; sessions without one fall back to the classifier's own bucket.
    """
    wanted = {sid: code for sid, code in first_errors.items() if code in NAMED_ERRORS}
    chosen: dict[str, dict] = {}
    for row in flat_rows:
        sid = (row.get("sessionId") or "").strip()
        if sid in wanted and sid not in chosen and (row.get("errorcode") or "").strip() == wanted[sid]:
            # enrichment columns may be absent from a flat export; the classifier only needs the code and status
            chosen[sid] = {**_stub_row(sid, wanted[sid]), **row, "sessionId": sid, "errorcode": wanted[sid]}
    rows = [chosen.get(sid) or _stub_row(sid, code) for sid, code in wanted.items()]
    events = build_events(rows, setup, pos, opco, date)
    return {e["sessionId"]: e["subcategory"] for e in events}
