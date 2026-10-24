from __future__ import annotations

import pytest
from conftest import load_script

mod = load_script("build_3016_subcategory_summary.py")

VIDEO = "Video decode error"
MSE = "MSE append failed (3014/3015)"


def _ev(sub: str, hh: str, sid: str, opco: str = "ZA") -> dict:
    return {"date": "2026-10-22", "opco": opco, "subcategory": sub, "householdId": hh, "sessionId": sid}


def test_counts_events_distinct_households_and_sessions() -> None:
    events = [_ev(VIDEO, "h1", "s1"), _ev(VIDEO, "h1", "s2"), _ev(VIDEO, "", ""), _ev(MSE, "h2", "s3")]
    rows = {r["subcategory"]: r for r in mod.build_summary(events)}
    assert rows[VIDEO]["events"] == 3
    assert rows[VIDEO]["households"] == 1
    assert rows[VIDEO]["sessions"] == 2
    assert rows[VIDEO]["priority"] == "P1"
    assert rows[MSE]["priority"] == "P3"
    assert list(rows[VIDEO]) == mod.SUMMARY_COLUMNS


def test_summary_event_total_equals_events_rows() -> None:
    events = [_ev(VIDEO, "h1", "s1"), _ev(MSE, "h2", "s2"), _ev("Mystery", "h3", "s3"), _ev(VIDEO, "h1", "s4", "GH")]
    rows = mod.build_summary(events)
    assert sum(r["events"] for r in rows) == len(events)
    assert {r["priority"] for r in rows if r["subcategory"] == "Mystery"} == {"P?"}
    assert mod.build_summary([]) == []


def test_mixed_dates_raise() -> None:
    other = {**_ev(VIDEO, "h1", "s1"), "date": "2026-10-23"}
    with pytest.raises(ValueError, match="multiple dates"):
        mod.build_summary([_ev(VIDEO, "h1", "s2"), other])
