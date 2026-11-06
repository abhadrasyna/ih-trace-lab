"""Offline tests for analyze_user_tenure (synthetic session rows only)."""
from __future__ import annotations

from datetime import date

import pytest

from scripts.analyze_user_tenure import (
    BUCKETS,
    TenureError,
    aggregate,
    build_households,
    bucket_for,
    read_sessions,
    row_count_table,
    summarise_buckets,
)

END = date(2026, 11, 5)
EARLIEST = date(2026, 10, 1)


def _row(sid, household, start, outcome="DESTROY", device="dev"):
    return {"sessionId": sid, "householdId": household, "deviceId": device, "playback_outcome": outcome,
            "event_start": start}


def _households(rows, earliest=EARLIEST):
    agg = aggregate(read_sessions(rows), EARLIEST, END)
    return agg, build_households(agg, active_since=EARLIEST, end_date=END, earliest=earliest, tenant="ZA")


def test_bucket_boundaries():
    got = {d: bucket_for(d) for d in (0, 7, 8, 30, 31, 90, 91, 180, 181)}
    assert got == {0: "0-7d", 7: "0-7d", 8: "8-30d", 30: "8-30d", 31: "31-90d", 90: "31-90d",
                   91: "91-180d", 180: "91-180d", 181: "180d+"}
    with pytest.raises(TenureError):
        bucket_for(-1)


def test_guest_ids_excluded_from_tenure():
    rows = [
        _row("s1", "h1", "2026-11-01 10:00:00"),
        _row("s2", "GUEST.abc", "2026-11-02 10:00:00", "EBVS"),
        _row("s3", "h2", "2026-11-02 10:00:00", device="GUEST.dev"),
    ]
    agg, households = _households(rows)
    assert [h["household_id"] for h in households] == ["h1"]
    assert agg.guest_ids == 2 and agg.guests.sessions == 2
    buckets = summarise_buckets(households, agg, END, "ZA", EARLIEST, cohort_ids=None, in_range=set())
    guest = [b for b in buckets if b["cohort"] == "guest"][0]
    assert (guest["households"], guest["sessions"], guest["successes"]) == (2, 2, 1)
    assert sum(b["households"] for b in buckets if b["cohort"] == "household") == 1


def test_first_seen_floor_flagged_as_censored():
    rows = [
        _row("a", "old", "2026-10-01 08:00:00"),
        _row("b", "old", "2026-11-05 08:00:00", "EBVS"),
        _row("c", "new", "2026-11-03 08:00:00"),
    ]
    agg, households = _households(rows)
    by_id = {h["household_id"]: h for h in households}
    assert by_id["old"]["censored"] is True and by_id["old"]["tenure_days"] == 35
    assert by_id["new"]["censored"] is False and by_id["new"]["bucket"] == "0-7d"
    assert "left-censored at 2026-10-01" in by_id["old"]["limits_note"]
    buckets = summarise_buckets(households, agg, END, "ZA", EARLIEST, cohort_ids=None, in_range=set())
    by_bucket = {b["bucket"]: b for b in buckets if b["cohort"] == "household"}
    assert set(by_bucket) == set(BUCKETS)  # empty buckets stay present
    assert by_bucket["91-180d"]["households"] == 0 and by_bucket["180d+"]["households"] == 0
    assert by_bucket["31-90d"]["households"] == 1 and by_bucket["31-90d"]["censored_households"] == 1
    assert by_bucket["31-90d"]["success_rate"] == 0.5 and by_bucket["31-90d"]["share"] == 0.5


def test_small_days_flagged_and_missing_listed():
    table = row_count_table({date(2026, 10, 1): 10, date(2026, 10, 2): 100, date(2026, 10, 3): 120},
                            [date(2026, 10, 4)], 0.25, "ZA", EARLIEST)
    assert [r["small_day"] for r in table[:3]] == [True, False, False]
    assert table[3]["session_rows"] == "missing"


def test_untimed_session_dated_by_file_day_not_dropped():
    rows = [{**_row("u1", "h1", "", "EBVS"), "_file_date": "2026-11-03"}, _row("u2", "h2", "")]
    agg = aggregate(read_sessions(rows), EARLIEST, END)
    assert agg.file_dated_sessions == 1 and agg.untimed_sessions == 1
    assert agg.households["h1"].dates == {date(2026, 11, 3)} and agg.households["h1"].attempts == 1
