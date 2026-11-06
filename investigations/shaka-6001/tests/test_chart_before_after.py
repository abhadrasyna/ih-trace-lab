"""Offline tests for chart_before_after (synthetic CSV rows, tmp_path only)."""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from scripts import chart_before_after as cba
from src.lib.charts.errors import ChartError

IST = ZoneInfo("Asia/Kolkata")
WEB = [
    {"webview_group": "webview", "events_before": "30", "events_after": "10"},
    {"webview_group": "non_webview", "events_before": "10", "events_after": "40"},
]
MODELS = [
    {"level": "model", "device_model": "P11", "events_before": "5", "events_after": "20"},
    {"level": "model", "device_model": "A1", "events_before": "10", "events_after": "10"},
    {"level": "model", "device_model": "B2", "events_before": "1", "events_after": "0"},
    {"level": "model_build", "device_model": "P11", "events_before": "99", "events_after": "99"},
]


def test_chart_values_from_counts():
    assert cba.non_webview_counts(WEB) == ([10, 40], [40, 50])
    assert cba.change_phrase(2.3, 5.5) == "more than doubled"
    assert cba.change_phrase(5.0, 5.1) == "held steady"
    names, values, total = cba.top_model_values(MODELS, top=2)
    assert (names, values, total) == (["P11", "A1"], [25.0, 20.0], 46)
    enriched = [
        {"datetime": "2026-11-04T10:00:00Z", "period": "before", "is_webview": "True"},
        {"datetime": "2026-11-04T11:00:00Z", "period": "before", "is_webview": "False"},
        {"datetime": "2026-11-04T19:00:00Z", "period": "after", "is_webview": "False"},  # 00:30 IST next day
        {"datetime": "2026-11-05T10:00:00Z", "period": "unknown", "is_webview": "True"},
    ]
    days, deltas, baseline = cba.daily_webview_delta(enriched, IST)
    assert days == ["2026-11-04", "2026-11-05"] and baseline == pytest.approx(50.0)
    assert deltas == pytest.approx([0.0, -50.0])


def test_chart_error_does_not_raise(tmp_path, monkeypatch):
    def boom() -> bytes:
        raise ChartError("bad input")

    enriched = [{"datetime": "2026-11-04T10:00:00Z", "period": "before", "is_webview": "True"},
                {"datetime": "2026-11-05T10:00:00Z", "period": "after", "is_webview": "False"}]
    chrome = [{"group": "155", "before_events": "3", "after_events": "1"},
              {"group": "156", "before_events": "0", "after_events": "4"}]
    charts = cba.build_charts(WEB, MODELS, enriched, chrome, tenant="ZA", start=date(2026, 11, 4),
                              end=date(2026, 11, 5), tz=IST)
    assert len(charts) == 4
    ok = cba.write_charts(charts, tmp_path, "ZA", lambda a: f"{a}.png")
    assert len(ok) == 4 and ok[0].read_bytes().startswith(b"\x89PNG")
    assert cba.write_charts({"6001_x": boom, **charts}, tmp_path, "ZA", lambda a: f"{a}.png") == ok


def test_each_chart_uses_its_own_data_and_bad_cell_is_skipped(tmp_path, monkeypatch):
    seen = {}

    def fake(labels, series, **kw):
        seen[kw["title"]] = (list(labels), kw.get("total"))
        return b"\x89PNG"

    monkeypatch.setattr(cba, "render_stacked_bar", fake)
    chrome = [{"group": "99", "before_events": "1", "after_events": "1"},
              {"group": "100", "before_events": "x", "after_events": "1"}]
    charts = cba.build_charts(WEB, MODELS, None, chrome, tenant="ZA", start=date(2026, 11, 4),
                              end=date(2026, 11, 5), tz=IST)
    written = cba.write_charts(charts, tmp_path, "ZA", lambda a: f"{a}.png")
    assert len(written) == 2  # chrome chart skipped on the bad cell
    assert not seen
    ordered = cba.chrome_version_values([{"group": g, "before_events": "1", "after_events": "0"} for g in ("100", "99")])
    assert ordered[0] == ["99", "100"]
