"""Tests for the pure merge model (no network)."""
from __future__ import annotations

from datetime import date

import pytest

from src.pipelines.usage_tracking.athena_source import DeviceSeen, ErrorRow, SessionRow
from src.pipelines.usage_tracking.errors import MergeError
from src.pipelines.usage_tracking.lightstep_source import RequestRow
from src.pipelines.usage_tracking.merge import TREND_DAYS, build_household_day, build_trend
from src.pipelines.usage_tracking.roster import Household, Member
from src.pipelines.usage_tracking.rules import IDLE_DAYS, apply_rules

DAY = date(2026, 11, 2)
HH = Household(hhid="H1", label="team", tenant="ZA", track=True, members=(Member("Sai", "d1"), Member("Fayaz", "d2")), phone="1")


def _s(sid: str, dev: str, start: str, end: str = "", outcome: str = "DESTROY", content: str = "Bluey", hh: str = "H1") -> SessionRow:
    return SessionRow(sid, hh, dev, content, "", outcome, start, end)


def test_person_metrics_and_idle_flag():
    sessions = [
        _s("s1", "d1", "2026-11-02 10:00:00", "2026-11-02 10:30:00"),
        _s("s2", "d1", "2026-11-02 11:00:00", "2026-11-02 11:15:00", content="Bluey"),
        _s("s3", "d1", "2026-11-02 12:00:00", "", outcome="PLAYER_ERROR", content="Other"),
    ]
    requests = [RequestRow("s1", "H1", "d1", "t1", 4), RequestRow("s2", "H1", "d1", "t2", 1)]
    hd = apply_rules(build_household_day(HH, DAY, sessions, [], [ErrorRow("s3", "6001", "", "", "")], requests))
    sai, fayaz = hd.people
    assert (sai.active, sai.sessions, sai.watch_minutes, sai.errors, sai.top_content, sai.lightstep_requests) == (True, 3, 45.0, 1, "Bluey", 5)
    assert (fayaz.active, fayaz.sessions, fayaz.top_content) == (False, 0, None)
    assert [f.kind for f in fayaz.flags] == ["idle"]
    assert IDLE_DAYS == 3 and not any(f.kind == "idle" for f in sai.flags)
    assert any(f.kind == "error_endreason" and "6001" in f.detail for f in sai.flags)


def test_new_device_flagged_on_tracked_household():
    seen = [DeviceSeen("H1", "d1", 2, "2026-11-02 09:00:00"), DeviceSeen("H1", "dX", 3, "2026-11-02 08:00:00")]
    hd = apply_rules(build_household_day(HH, DAY, [], seen, [], []))
    flags = [f for f in hd.flags if f.kind == "new_device"]
    assert [(f.device_id, f.detail) for f in flags] == [("dX", "not in roster; first seen 2026-11-02 08:00:00, 3 sessions")]


def test_untracked_household_never_flagged():
    hh = Household(hhid="H1", label="team", tenant="ZA", track=False, members=HH.members)
    hd = apply_rules(build_household_day(hh, DAY, [], [DeviceSeen("H1", "dX", 3, "2026-11-02 08:00:00")], [], []))
    assert not [f for f in hd.flags if f.kind == "new_device"]


def test_mismatch_flag_when_session_only_in_athena():
    sessions = [_s("s1", "d1", "2026-11-02 10:00:00"), _s("s2", "d1", "2026-11-02 11:00:00")]
    hd = apply_rules(build_household_day(HH, DAY, sessions, [], [], [RequestRow("s1", "H1", "d1", "t1", 1), RequestRow("s9", "H1", "d2", "t9", 1)]))
    details = sorted(f.detail for f in hd.flags if f.kind == "mismatch")
    assert details == ["s2 in Athena only", "s9 in Lightstep only"]
    assert [f.kind for f in hd.people[1].flags if f.kind == "mismatch"] == ["mismatch"]


def test_lightstep_session_from_previous_day_is_not_a_mismatch():
    sessions = [_s("s0", "d1", "2026-11-01 23:50:00"), _s("s1", "d1", "2026-11-02 10:00:00")]
    hd = apply_rules(build_household_day(HH, DAY, sessions, [], [], [RequestRow("s0", "H1", "d1", "t0", 1), RequestRow("s1", "H1", "d1", "t1", 1)]))
    assert not [f for f in hd.flags if f.kind == "mismatch"]


def test_unparseable_start_raises():
    with pytest.raises(MergeError):
        build_household_day(HH, DAY, [_s("s1", "d1", "garbage")], [], [], [])


def test_lightstep_traces_grouped_per_session():
    requests = [RequestRow("s1", "H1", "d1", "t2", 1), RequestRow("s1", "H1", "d1", "t1", 1), RequestRow("s9", "H1", "other", "t3", 1)]
    hd = build_household_day(HH, DAY, [], [], [], requests)
    assert dict(hd.lightstep_traces) == {"s1": ("t1", "t2")}


def test_trend_has_seven_days_with_zeros():
    sessions = [_s("s1", "d1", "2026-10-27 10:00:00"), _s("s2", "d1", "2026-11-02 10:00:00"), _s("s3", "d1", "2026-10-26 10:00:00")]
    trend = build_trend(sessions, HH, DAY)
    assert trend["d1"] == (1, 0, 0, 0, 0, 0, 1) and len(trend["d1"]) == TREND_DAYS
    assert trend["d2"] == (0,) * TREND_DAYS
