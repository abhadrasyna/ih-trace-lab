from datetime import date
from zoneinfo import ZoneInfo

import pytest

from scripts import rank_daily_top_models as mod
from scripts.lib.day_basis import DayBasis

IST = ZoneInfo("Asia/Kolkata")


def ev(model="P11", dev="d1", sess="s1", **kw):
    row = {"datetime": "2026-11-04T05:00:00Z", "household_id": "h1", "device_id": dev, "session_id": sess,
           "device_model": model, "build_id": "B1", "os_name": "Android", "os_version": "14",
           "chrome_version": "150.0", "is_webview": "True", "ua_shape": "android_build", "period": "before",
           "app_version": "v1"}
    return row | kw


def table(rows, min_events=20, top=10):
    by_day = mod.assign_days(rows, DayBasis.IST, IST, date(2026, 11, 4), date(2026, 11, 5))
    return mod.build_table(by_day, top, min_events, "ZA", DayBasis.IST)


def test_one_model_across_builds_is_one_row():
    rows = [ev(build_id="B1"), ev(build_id="B2", dev="d2"), ev(build_id="B2", dev="d3"), ev(model="X", dev="d4")]
    out = table(rows)
    assert [(r["rank"], r["model"], r["events_6001"], r["distinct_devices"], r["top_build"]) for r in out] == [
        (1, "P11", 3, 3, "B2"), (2, "X", 1, 1, "B1")]
    assert out[0]["share_of_day_pct"] == 75.0 and out[0]["day_events"] == 4


def test_unparsed_ua_gets_own_row():
    rows = [ev(model="K (device masked - UA reduction)", ua_shape="android_reduced"),
            ev(model="Desktop (Linux)", ua_shape="desktop", os_name="Linux", os_version=""),
            ev(model="", ua_shape="unparsed", device_id="GUEST.x", household_id="GUEST.y")]
    out = {r["model"]: r for r in table(rows)}
    assert set(out) == {"K (device masked - UA reduction)", "Desktop (Linux)", mod.NO_UA_LABEL}
    assert out["Desktop (Linux)"]["top_android_version"] == mod.UNKNOWN
    assert out[mod.NO_UA_LABEL]["guest_events"] == 1  # guest event still counted


def test_low_traffic_model_flagged():
    rows = [ev() for _ in range(3)] + [ev(model="Q", dev="d9")]
    out = {r["model"]: r for r in table(rows, min_events=2)}
    assert out["P11"]["low_traffic"] is False and out["Q"]["low_traffic"] is True


def test_missing_columns_raise():
    with pytest.raises(mod.RankModelsError):
        mod.validate([{"datetime": "x"}])
