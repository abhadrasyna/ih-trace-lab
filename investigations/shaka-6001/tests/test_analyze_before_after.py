"""Offline tests for analyze_before_after (synthetic enriched rows, tmp_path only)."""
from __future__ import annotations

import csv

import pytest

from scripts.analyze_before_after import MODEL_FIELDS, BeforeAfterError, read_enriched, summarize, write_rows


def _row(period, device, session, *, wv="True", model="P11", build="TP1A"):
    return {"period": period, "device_id": device, "session_id": session, "is_webview": wv,
            "device_model": model, "build_id": build}


def _by(rows, key, value):
    return next(r for r in rows if r[key] == value)


def test_webview_split_counts():
    rows = [_row("before", "d1", "s1"), _row("before", "d1", "s2"), _row("before", "d2", "s3", wv="False"),
            _row("after", "d1", "s4"), _row("after", "GUEST.x", "s5"), _row("after", "d3", "s6", wv=""),
            _row("unknown", "d9", "s9")]
    web, _, counts = summarize(rows, "ZA")
    wv, non, unk = (_by(web, "webview_group", g) for g in ("webview", "non_webview", "unknown"))
    assert (wv["events_before"], wv["devices_before"], wv["sessions_before"]) == (2, 1, 2)
    assert (wv["events_after"], wv["devices_after"], wv["guest_devices_after"]) == (2, 1, 1)
    assert non["events_before"] == 1 and non["share_before_pct"] == pytest.approx(33.33)
    assert wv["share_before_pct"] == pytest.approx(66.67) and wv["share_change_pp"] == pytest.approx(0.0)
    assert unk["events_after"] == 1
    assert counts == {"before": 3, "after": 3, "unknown": 1}


def test_model_and_build_levels():
    rows = [_row("before", "d1", "s1", build="A"), _row("after", "d2", "s2", build="B")]
    _, models, _ = summarize(rows, "ZA")
    assert _by([m for m in models if m["level"] == "model"], "device_model", "P11")["events_after"] == 1
    builds = [m for m in models if m["level"] == "model_build"]
    assert {m["build_id"] for m in builds} == {"A", "B"}


def test_empty_period_yields_zero_not_error():
    web, models, counts = summarize([_row("after", "d1", "s1")], "ZA")
    wv = _by(web, "webview_group", "webview")
    assert wv["events_before"] == 0 and wv["share_before_pct"] == 0.0 and wv["share_change_pp"] == 100.0
    assert _by(web, "webview_group", "non_webview")["events_after"] == 0
    empty_web, empty_models, _ = summarize([], "ZA")
    assert empty_models == [] and all(r["events_before"] == r["events_after"] == 0 for r in empty_web)
    assert counts["before"] == 0 and models


def test_missing_columns_raise():
    with pytest.raises(BeforeAfterError):
        summarize([{"period": "before"}], "ZA")


def test_read_enriched_missing_file_raises(tmp_path):
    with pytest.raises(BeforeAfterError):
        read_enriched(tmp_path / "missing.csv")


def test_write_rows_roundtrip(tmp_path):
    out = tmp_path / "n" / "m.csv"
    _, models, _ = summarize([_row("before", "d1", "s1")], "ZA")
    write_rows(out, models, MODEL_FIELDS)
    write_rows(out, models, MODEL_FIELDS)
    with open(out, newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == len(models)
    assert not list(out.parent.glob("*.tmp"))
