"""Offline tests for analyze_session_error_impact (synthetic rows and tmp_path files only)."""
from __future__ import annotations

import json
from datetime import date

import pytest

from scripts import analyze_session_error_impact as asei
from scripts.lib.local_data import LocalDataError

D1, D2 = date(2026, 11, 1), date(2026, 11, 2)


def _err(sid, code=6001, eventid="PLAYER_ERROR"):
    desc = {"errordescription": f"E8{code} : x", "shakaerror": {"code": code}}
    data = {"sessionid": sid, "errorcode": code, "errordescription": desc} if sid else {"errordescription": desc}
    return {"datetime": "2026-11-01T00:00:00Z", "messageid": "m", "clientid": "d:h", "eventclass": "PLAYER",
            "eventid": eventid, "eventdata": json.dumps(data)}


def _sets(sessions, error, code):
    return asei.DaySets(frozenset(sessions), frozenset(error), frozenset(code))


def test_error_sessions_dedupe_mixed_codes_and_non_errors():
    rows = [_err("a"), _err("a"), _err("b", 1003), _err("b", 6001), _err("c", 3016), _err("z", eventid="PLAYER_STATE"),
            _err(None)]
    errors, with_6001, unattributed = asei.error_session_ids(rows)
    assert errors == {"a", "b", "c"} and with_6001 == {"a", "b"} and unattributed == 1


def test_is_6001_falls_back_to_errorcode():
    assert asei.is_6001({"shaka_code": 6001}) and asei.is_6001({"shaka_code": None, "errorcode": "6001"})
    assert not asei.is_6001({"shaka_code": 1003, "errorcode": 6001}) and not asei.is_6001({})


def test_row_counts_unmatched_error_session_and_bounded_pcts():
    row = asei.impact_row("2026-11-01", _sets("abcd", {"a", "b", "x"}, {"a", "x"}), "ZA")
    assert (row["unique_sessions"], row["error_sessions"], row["sessions_6001"], row["other_error_sessions"]) == (4, 3, 2, 1)
    assert (row["error_sessions_in_session_file"], row["sessions_6001_in_session_file"]) == (2, 1)
    assert row["pct_error_of_unique"] == "50.00" and row["pct_6001_of_unique"] == "25.00"
    assert row["pct_other_error_of_unique"] == "25.00" and row["pct_6001_of_error_sessions"] == "66.67"
    assert row["day_basis"] == "utc"


def test_only_error_sessions_never_exceed_100_and_empty_day_is_blank():
    row = asei.impact_row("d", _sets({"a"}, {"x", "y", "a"}, {"x", "y"}), "ZA")
    assert float(row["pct_error_of_unique"]) <= 100 and row["pct_6001_of_error_sessions"] == "66.67"
    empty = asei.impact_row("d", _sets(set(), set(), set()), "ZA")
    assert empty["pct_error_of_unique"] == "" and empty["pct_6001_of_error_sessions"] == ""


def test_all_row_is_distinct_union_across_days():
    table = asei.build_table({D1: _sets({"a", "b"}, {"a"}, {"a"}), D2: _sets({"a", "c"}, {"a", "c"}, set())}, "ZA")
    assert [r["day"] for r in table] == ["2026-11-01", "2026-11-02", "all"]
    total = table[-1]
    assert (total["unique_sessions"], total["error_sessions"], total["sessions_6001"], total["other_error_sessions"]) == (3, 2, 1, 1)


def test_session_ids_requires_column():
    assert asei.session_ids([{"sessionId": " a "}, {"sessionId": ""}, {"sessionId": "a"}]) == {"a"}
    with pytest.raises(LocalDataError):
        asei.session_ids([{"foo": "1"}])


def _write_day(folder, day, sessions, errors):
    (folder / f"{day}_session.csv").write_text("sessionId,householdId\n" + "".join(f"{s},h\n" for s in sessions))
    import csv
    with open(folder / f"{day}_error_eventdata.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["datetime", "messageid", "clibversion", "clientid", "eventclass", "eventid", "eventdata"])
        w.writeheader()
        for e in errors:
            w.writerow({k: e.get(k, "") for k in w.fieldnames})


def test_load_day_sets_and_missing_day_fails_loudly(tmp_path):
    _write_day(tmp_path, "2026-11-01", ["a", "b"], [_err("a"), _err("q", 1003)])
    per_day, unattributed = asei.load_day_sets([tmp_path], [D1])
    assert per_day[D1] == _sets({"a", "b"}, {"a", "q"}, {"a"}) and unattributed == 0
    with pytest.raises(LocalDataError, match="2026-11-02"):
        asei.load_day_sets([tmp_path], [D1, D2])
