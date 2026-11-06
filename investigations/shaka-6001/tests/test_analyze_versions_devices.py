"""Offline tests for analyze_versions_devices (synthetic rows, tmp_path only)."""
from __future__ import annotations

import pytest

from scripts.analyze_versions_devices import (
    VersionsDevicesError,
    android_version,
    chrome_major,
    drm_tables,
    fail_then_success_devices,
    load_enriched,
    mixed_webview_devices,
    version_table,
    write_table,
)


def _row(device, *, period="before", chrome="156.0.8078.47", wv=True, ts="2026-11-05T00:00:00Z",
         os_version="13", household="hh"):
    return {"device_id": device, "household_id": household, "period": period, "chrome_version": chrome,
            "os_name": "Android", "os_version": os_version, "is_webview": str(wv), "datetime": ts,
            "device_model": "P11"}


def test_chrome_major_grouping():
    assert chrome_major("156.0.8078.47") == "156" and chrome_major("") == "unknown" and chrome_major("x.1") == "unknown"
    rows = [_row("a", chrome="156.0.1"), _row("b", chrome="156.0.2"), _row("c", period="after", chrome="157.0.1"),
            _row("d", period="unknown", chrome="158.0.1")]
    table = {r["group"]: r for r in version_table(rows, lambda r: chrome_major(r["chrome_version"]), "ZA")}
    assert set(table) == {"156", "157"}  # unknown period excluded
    assert (table["156"]["before_events"], table["156"]["before_share"], table["156"]["before_devices"]) == (2, 1.0, 2)
    assert table["157"]["share_change"] == 1.0 and table["156"]["share_change"] == -1.0


def test_android_version_buckets_non_android():
    assert android_version(_row("a")) == "13"
    assert android_version({"os_name": "Windows", "os_version": "10.0"}) == "non-android"


def test_mixed_webview_device_flagged():
    rows = [_row("a", wv=True), _row("a", wv=False), _row("b", wv=True), _row("c", wv=False)]
    mixed = mixed_webview_devices(rows, "ZA")
    assert [(m["device_id"], m["webview_events"], m["non_webview_events"]) for m in mixed] == [("a", 1, 1)]


def test_fail_then_success_uses_destroy_only_and_later_time():
    rows = [_row("a", ts="2026-11-05T10:00:00Z"), _row("b", ts="2026-11-05T10:00:00Z"),
            _row("c", ts="2026-11-05T10:00:00Z")]
    outcomes = [
        {"device_id": "a", "session_id": "1", "playback_outcome": "DESTROY", "datetime": "2026-11-05T11:00:00Z"},
        {"device_id": "b", "session_id": "2", "playback_outcome": "EBVS", "datetime": "2026-11-05T11:00:00Z"},
        {"device_id": "c", "session_id": "3", "playback_outcome": "DESTROY", "datetime": "2026-11-05T09:00:00Z"},
    ]
    result = fail_then_success_devices(rows, outcomes, "ZA")
    assert [r["device_id"] for r in result] == ["a"]


def test_drm_summary_counts_and_rates():
    rows = [_row("a"), _row("a"), _row("b"), _row("c")]
    _, summary = drm_tables(rows, {"a": "true", "b": "false"}, "ZA")
    by_value = {s["drmenabled"]: s for s in summary}
    assert (by_value["true"]["devices"], by_value["true"]["events"]) == (1, 2)
    assert by_value["unknown"]["devices"] == 1 and by_value["false"]["device_share"] == pytest.approx(1 / 3, abs=1e-5)


def test_missing_input_and_columns_raise(tmp_path):
    with pytest.raises(VersionsDevicesError):
        load_enriched(tmp_path / "absent.csv")
    bad = tmp_path / "bad.csv"
    bad.write_text("device_id,period\na,before\n", encoding="utf-8")
    with pytest.raises(VersionsDevicesError):
        load_enriched(bad)


def test_write_table_is_idempotent(tmp_path):
    out = tmp_path / "n" / "t.csv"
    rows = version_table([_row("a")], lambda r: "x", "ZA")
    write_table(out, rows, list(rows[0]))
    write_table(out, rows, list(rows[0]))
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2 and not list(out.parent.glob("*.tmp"))
