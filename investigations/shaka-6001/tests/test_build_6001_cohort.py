"""Offline tests for build_6001_cohort (synthetic rows, fake Athena client, tmp_path only)."""
from __future__ import annotations

import csv
from datetime import date

import pytest

from scripts.build_6001_cohort import (
    CohortError,
    FIELDNAMES,
    SESSION_FIELDNAMES,
    attach_session_counts,
    build_cohort,
    ensure_sessions,
    write_cohort,
)
from src.lib.athena.protocols import QueryResult

DAYS = [date(2026, 11, 4), date(2026, 11, 5)]


def _event(device, household, ts, period, webview="True", model="P11", code="6001"):
    return {"datetime": ts, "device_id": device, "household_id": household, "shaka_code": code,
            "period": period, "period_conflict": "False", "is_webview": webview, "device_model": model}


class FakeClient:
    def __init__(self):
        self.sql = []

    def start_query(self, sql, params):
        self.sql.append(sql)
        return f"id{len(self.sql)}"

    def poll_status(self, execution_id):
        return "SUCCEEDED"

    def fetch_results(self, execution_id):
        row = {"sessionId": "s1", "householdId": "hh1", "deviceId": "d1", "playback_outcome": "DESTROY"}
        return QueryResult(execution_id, [row], "SUCCEEDED")


def test_cohort_first_6001_and_period():
    rows = [
        _event("d1", "hh1", "2026-11-05T09:00:00Z", "after", webview="False"),
        _event("d1", "hh1", "2026-11-03T18:40:00Z", "before"),  # earliest, UTC 18:40 = next day IST
        _event("d1", "hh1", "2026-11-04T10:00:00Z", "after"),
        _event("d2", "GUEST.abc", "2026-11-04T10:00:00Z", "after"),
        _event("d3", "hh3", "2026-11-04T10:00:00Z", "after", code="7001"),
        _event("", "hh4", "2026-11-04T10:00:00Z", "after"),
    ]
    built = build_cohort(rows)
    cohort, skipped = built.members, built.skipped_rows
    by_key = {m["clientid"]: m for m in cohort}
    assert set(by_key) == {"d1:hh1", "d2:GUEST.abc"} and skipped == 1
    first = by_key["d1:hh1"]
    assert (first["period"], first["is_webview"], first["events_6001"]) == ("before", "True", 3)
    assert first["first_6001_date_ist"] == "2026-11-04"
    assert by_key["d2:GUEST.abc"]["is_guest"] and not first["is_guest"]


def test_missing_session_rows_reported(tmp_path):
    cohort = build_cohort([_event("d1", "hh1", "2026-11-04T10:00:00Z", "after"),
                           _event("d9", "hh9", "2026-11-05T10:00:00Z", "after")]).members
    save_dir, client = tmp_path / "data", FakeClient()
    (save_dir).mkdir()
    (save_dir / "2026-11-04_session.csv").write_text(
        ",".join(SESSION_FIELDNAMES) + "\ns0,hh0,d0,c,DESTROY,,,,,\n", encoding="utf-8")
    rows, missing = ensure_sessions([save_dir], save_dir, DAYS, "db1", lambda: client)
    assert len(client.sql) == 1 and "2026-11-05" in client.sql[0] and "db1" in client.sql[0]
    assert missing == [] and len(rows) == 2
    coverage = attach_session_counts(cohort, rows)
    assert (coverage.members, coverage.with_sessions, coverage.without_sessions) == (2, 1, 1)
    assert "without_session_rows=1" in coverage.line("ZA")
    out = tmp_path / "cohort.csv"
    write_cohort(out, cohort)
    written = list(csv.DictReader(out.open(encoding="utf-8")))
    assert list(written[0]) == FIELDNAMES
    assert {r["clientid"]: r["has_session_rows"] for r in written} == {"d1:hh1": "True", "d9:hh9": "False"}
    ensure_sessions([save_dir], save_dir, DAYS, "db1", lambda: client)
    assert len(client.sql) == 1  # nothing refetched


def test_unreadable_timestamps_counted_and_ambiguous_ids_skipped():
    built = build_cohort([_event("a", "b:c", "garbage", "after"), _event("a:b", "c", "2026-11-04T10:00:00Z", "before")])
    assert [m["clientid"] for m in built.members] == ["a:b:c"] and built.skipped_rows == 1
    assert built.bad_timestamp_rows == 1 and built.members_without_timestamp == 1


def test_guards_unsettled_dates_and_foreign_session_files(tmp_path):
    with pytest.raises(CohortError):
        ensure_sessions([tmp_path], tmp_path, DAYS, "db1", FakeClient, settled_before=DAYS[1])
    with pytest.raises(CohortError):
        attach_session_counts([], [{"sessionId": "s1"}])
