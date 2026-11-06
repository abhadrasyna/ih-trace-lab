"""Offline tests for analyze_6001_recovery (synthetic rows, tmp_path only)."""
from __future__ import annotations

from scripts.analyze_6001_recovery import (
    COHORT_GUEST,
    COHORT_HOUSEHOLD,
    STATUS_NO_SESSIONS,
    analyse_members,
    sessions_by_member,
    sessions_with_6001,
    summarise,
)

FIRST = "2026-11-04T10:00:00+00:00"  # 15:30 IST on 2026-11-04


def _member(device, household, is_guest=False, period="after", webview="True", model="P11", first=FIRST):
    return {"device_id": device, "household_id": household, "is_guest": str(is_guest), "first_6001_utc": first,
            "first_6001_ist": first, "period": period, "is_webview": webview, "device_model": model}


def _session(device, household, sid, outcome, start, end=""):
    return {"deviceId": device, "householdId": household, "sessionId": sid, "playback_outcome": outcome,
            "event_start": start, "event_end": end}


def _run(members, sessions, six=()):
    six_map = sessions_with_6001([{"device_id": d, "household_id": h, "session_id": s, "shaka_code": "6001"}
                                  for d, h, s in six])
    return analyse_members(members, sessions_by_member(sessions), six_map, "ZA")


def test_same_day_and_cross_day_recovery_split():
    members = [_member("d1", "h1"), _member("d2", "h2"), _member("d3", "h3"), _member("d4", "h4")]
    sessions = [
        _session("d1", "h1", "a0", "DESTROY", "2026-11-04 09:00:00"),  # before the first 6001
        _session("d1", "h1", "a1", "DESTROY", "2026-11-04 11:00:00"),  # cross-session, same IST day
        _session("d2", "h2", "b1", "DESTROY", "2026-11-05 11:00:00"),  # cross-session, later day
        _session("d3", "h3", "c1", "DESTROY", "2026-11-04 10:00:05", "2026-11-04 10:05:00"),  # same session as the 6001
        _session("d4", "h4", "e1", "EBVS", "2026-11-04 12:00:00"),  # never succeeds
    ]
    rows = {r["device_id"]: r for r in _run(members, sessions, six=[("d3", "h3", "c1")])}
    assert rows["d1"]["success_before"] == 1 and rows["d1"]["success_after"] == 1 and rows["d1"]["success_same_day"] == 1
    assert rows["d1"]["recovery_path"] == "cross_session" and rows["d1"]["minutes_to_next_success"] == 60.0
    assert rows["d2"]["success_same_day"] == 0 and rows["d2"]["success_after"] == 1
    assert rows["d3"]["recovery_path"] == "same_session" and rows["d3"]["success_after"] == 0
    assert rows["d4"]["never_recovered"] is True and rows["d4"]["recovered"] is False
    summary = {(r["dimension"], r["group"]): r for r in summarise(list(rows.values()), "ZA", 20)}
    period = summary[("period", "after")]
    assert (period["members"], period["recovered"], period["recovery_rate"]) == (4, 3, 0.75)
    assert (period["same_session"], period["cross_session"]) == (1, 2)
    assert (period["cross_same_day"], period["cross_later_day"], period["never_recovered"]) == (1, 1, 1)
    assert period["tenant"] == "ZA" and period["low_n"] is True


def test_guest_cohort_kept_separate():
    members = [_member("d1", "h1"), _member("GUEST.x", "GUEST.y", is_guest=True), _member("d5", "h5")]
    sessions = [
        _session("d1", "h1", "a1", "DESTROY", "2026-11-04 11:00:00"),
        _session("GUEST.x", "GUEST.y", "g1", "DESTROY", "2026-11-04 11:00:00"),
    ]
    rows = _run(members, sessions)
    assert {r["cohort"] for r in rows if r["device_id"].startswith("GUEST")} == {COHORT_GUEST}
    summary = summarise(rows, "ZA", 1)
    real = next(r for r in summary if r["cohort"] == COHORT_HOUSEHOLD and r["dimension"] == "period")
    guest = next(r for r in summary if r["cohort"] == COHORT_GUEST and r["dimension"] == "period")
    assert (real["members"], real["recovered"]) == (1, 1)
    assert (guest["members"], guest["recovered"]) == (1, 1)
    assert real["members_without_session_rows"] == 1  # d5: counted, not a failure
    assert next(r for r in rows if r["device_id"] == "d5")["status"] == STATUS_NO_SESSIONS
