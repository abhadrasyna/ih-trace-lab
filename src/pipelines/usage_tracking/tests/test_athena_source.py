"""Tests for the Athena session and error source (no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.pipelines.usage_tracking.athena_source import (
    LiveAthenaSource,
    LocalExportSource,
    SessionRow,
    debug_table_name,
)
from src.pipelines.usage_tracking.errors import AthenaSourceError, UsageTrackingError
from src.pipelines.usage_tracking.roster import Household, Member

DAY = date(2026, 11, 2)
HH = Household(hhid="H1", label="team", tenant="ZA", track=True, members=(Member("Sai", "d1"), Member("Fayaz", "d2")), phone="1")
SESSION_HEADER = "sessionId,householdId,deviceId,content,playback_outcome,event_start,event_end,startup_time_ms,buffering_count,buffering_total_ms\n"
DEBUG_HEADER = "sessionId,eventid,state,position,errorcode,errordescription,datetime\n"


def _export(tmp_path: Path, sessions: str, debug: str | None = DEBUG_HEADER) -> Path:
    folder = tmp_path / "ZA"
    folder.mkdir()
    (folder / f"{DAY}_session.csv").write_text(SESSION_HEADER + sessions)
    if debug is not None:
        (folder / f"{DAY}_debug_states.csv").write_text(debug)
    return tmp_path


class FakeRunner:
    def __init__(self, session_rows=None, error_rows=None, tables=None, boom=None):
        self.calls: list[str] = []
        self._session_rows = session_rows or []
        self._error_rows = error_rows or []
        self._tables = tables or [{"tab_name": "e6auj7k7_ccl_debug_events"}]
        self._boom = boom

    def __call__(self, sql: str) -> list[dict[str, str]]:
        self.calls.append(sql)
        if self._boom:
            raise self._boom
        if sql.startswith("SHOW TABLES"):
            return self._tables
        return self._error_rows if "PLAYER_ERROR" in sql else self._session_rows


def _live(runner: FakeRunner, today: date = DAY) -> LiveAthenaSource:
    return LiveAthenaSource("ZA", "e6auj7k7", runner, today)


LIVE_ROW = {
    "parent_session_id": "s1", "user_id": "H1", "device_id": "d1", "content": "Bluey", "content_id": "c1",
    "endreason": "PLAYER_ERROR", "event_start": "2026-11-02 10:00:00", "event_end": "",
}


def test_fetch_sessions_maps_rows():
    runner = FakeRunner(session_rows=[LIVE_ROW])
    rows = _live(runner).fetch_sessions([HH], DAY)
    assert rows == [SessionRow("s1", "H1", "d1", "Bluey", "c1", "PLAYER_ERROR", "2026-11-02 10:00:00", "")]
    assert "user_id = 'H1'" in runner.calls[0] and "device_id IN ('d1', 'd2')" in runner.calls[0]
    assert "unified_e6auj7k7" in runner.calls[0]


def test_errors_fetched_only_for_errored_sessions():
    runner = FakeRunner()
    ok = SessionRow("s1", "H1", "d1", "Bluey", "", "DESTROY", "", "")
    assert _live(runner).fetch_errors([ok], DAY) == []
    assert runner.calls == []


def test_errors_query_uses_clientid_and_keeps_only_errored_session_ids():
    err = {"datetime": "t", "clientid": "d1:H1", "session_id": "s1", "error_code": "6001", "message": "boom", "position": "0"}
    runner = FakeRunner(error_rows=[err, {**err, "session_id": "other"}])
    bad = SessionRow("s1", "H1", "d1", "Bluey", "", "PLAYER_ERROR", "", "")
    out = _live(runner).fetch_errors([bad], DAY)
    assert [e.session_id for e in out] == ["s1"] and out[0].error_code == "6001"
    assert "'d1:H1'" in runner.calls[-1] and "e6auj7k7_ccl_debug_events" in runner.calls[-1]


def test_client_error_is_wrapped():
    with pytest.raises(AthenaSourceError) as info:
        _live(FakeRunner(boom=RuntimeError("throttled"))).fetch_sessions([HH], DAY)
    assert isinstance(info.value, UsageTrackingError)


def test_unsafe_device_id_is_rejected_before_any_query():
    runner = FakeRunner()
    bad = Household("H1", "x", "ZA", True, (Member("Eve", "d1' OR '1'='1"),), "1")
    with pytest.raises(AthenaSourceError):
        _live(runner).fetch_sessions([bad], DAY)
    assert runner.calls == []


def test_local_reader_filters_by_household_and_device(tmp_path):
    rows = (
        "s1,H1,d1,Bluey,PLAYER_ERROR,2026-11-02 10:00:00,,1,0,0\n"
        "s2,H1,dX,Other,DESTROY,2026-11-02 11:00:00,,1,0,0\n"
        "s3,H9,d1,Elsewhere,DESTROY,2026-11-02 12:00:00,,1,0,0\n"
    )
    source = LocalExportSource("ZA", _export(tmp_path, rows))
    assert [s.session_id for s in source.fetch_sessions([HH], DAY)] == ["s1"]
    seen = source.fetch_household_devices(HH, DAY)
    assert [(d.device_id, d.session_count) for d in seen] == [("d1", 1), ("dX", 1)]


def test_local_errors_come_from_debug_states_for_errored_sessions_only(tmp_path):
    debug = DEBUG_HEADER + "s1,PLAYER_ERROR,,0,6001,Shaka,2026-11-02T10:00:01Z\ns2,PLAYER_ERROR,,0,1001,,2026-11-02T11:00:01Z\n"
    source = LocalExportSource("ZA", _export(tmp_path, "s1,H1,d1,Bluey,PLAYER_ERROR,a,,1,0,0\n", debug))
    sessions = source.fetch_sessions([HH], DAY)
    assert [(e.session_id, e.error_code, e.message) for e in source.fetch_errors(sessions, DAY)] == [("s1", "6001", "Shaka")]


def test_missing_local_file_raises(tmp_path):
    with pytest.raises(AthenaSourceError):
        LocalExportSource("ZA", tmp_path).fetch_sessions([HH], DAY)


def test_missing_debug_file_raises_only_when_a_session_errored(tmp_path):
    source = LocalExportSource("ZA", _export(tmp_path, "s1,H1,d1,Bluey,DESTROY,a,,1,0,0\n", debug=None))
    ok = source.fetch_sessions([HH], DAY)
    assert source.fetch_errors(ok, DAY) == []
    with pytest.raises(AthenaSourceError):
        source.fetch_errors([SessionRow("s1", "H1", "d1", "", "", "PLAYER_ERROR", "", "")], DAY)


def test_other_tenant_household_is_rejected(tmp_path):
    other = Household("H2", "x", "GH", True, (), "1")
    with pytest.raises(AthenaSourceError):
        LocalExportSource("ZA", tmp_path).fetch_sessions([other], DAY)


def test_debug_table_name_by_month():
    tables = ["e6auj7k7_ccl_debug_events", "e6auj7k7_ccl_debug_events_oct26", "e6auj7k7_ccl_debug_events_sept26"]
    today = date(2026, 11, 4)
    assert debug_table_name("e6auj7k7", date(2026, 11, 2), today, tables) == "e6auj7k7_ccl_debug_events"
    assert debug_table_name("e6auj7k7", date(2026, 10, 30), today, tables) == "e6auj7k7_ccl_debug_events_oct26"
    assert debug_table_name("e6auj7k7", date(2026, 9, 30), today, tables) == "e6auj7k7_ccl_debug_events_sept26"
    with pytest.raises(AthenaSourceError):
        debug_table_name("e6auj7k7", date(2026, 8, 1), today, tables)
