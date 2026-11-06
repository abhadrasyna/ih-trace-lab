"""Offline tests for analyze_guest_login_redirects (synthetic rows, tmp_path only)."""
from __future__ import annotations

import csv
import json

import pytest

from scripts import analyze_guest_login_redirects as mod
from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config

CONFIG = load_config(DEFAULT_CONFIG_PATH)
OLD, NEW = "v2026.10.27.01", "v2026.11.03.02"
WEBVIEW_UA = "Mozilla/5.0 (Linux; Android 13; P11 Build/TP1A; wv) AppleWebKit/537.36 Chrome/156.0.0.0 Mobile Safari/537.36"


def _redirect(device, ts, *, step=1, total=1, end="true"):
    return {"user_id": f"GUEST.{device}", "device_id": device, "nav_event_time": ts, "nav_step_num": str(step),
            "nav_step_total": str(total), "nav_end_event": end}


def _debug(device, ts, eventid, data, user=None):
    return {"datetime": ts, "clientid": f"{device}:{user or 'GUEST.' + device}", "eventclass": "c", "eventid": eventid,
            "eventdata": json.dumps(data)}


def _discovery(device, ts, version, ua="Mozilla/5.0 (Linux; Android 13; K) Chrome/156.0.0.0"):
    return _debug(device, ts, "APP_DISCOVERY", {"appversion": version, "deviceinfo": {"browserversion": ua}})


def test_guests_classified_by_app_version_inside_window():
    # 16:45 IST on 2026-11-04 is 11:15 UTC: inside the upgrade window, so only the version decides.
    redirects = [_redirect("old", "2026-11-04 11:15:00.000"), _redirect("new", "2026-11-04 11:20:00.000"),
                 _redirect("none", "2026-11-04 11:25:00.000")]
    debug = [_discovery("old", "2026-11-04T11:00:00.000Z", OLD), _discovery("new", "2026-11-04T11:00:00.000Z", NEW)]
    tables = mod.analyse(redirects, debug, CONFIG)
    periods = {r["period"]: r for r in tables["periods"]}
    assert (periods["before"]["guest_ids"], periods["after"]["guest_ids"], periods["unknown"]["guest_ids"]) == (1, 1, 1)
    assert tables["daily"][0]["guests_before"] == 1 and tables["daily"][0]["ist_day"] == "2026-11-04"
    assert periods["all"]["debug_match_rate"] == pytest.approx(2 / 3)


def test_guest_ids_counted_not_households():
    redirects = [_redirect("g1", "2026-11-05 03:00:00.000", step=1, total=2, end="false"),
                 _redirect("g1", "2026-11-05 03:00:05.000", step=2, total=2),
                 _redirect("g2", "2026-11-05 04:00:00.000")]
    debug = [_discovery("g1", "2026-11-05T02:59:00.000Z", NEW), _discovery("g2", "2026-11-05T03:59:00.000Z", NEW),
             _debug("g2", "2026-11-05T03:59:30.000Z", "APP_STATE_CHANGE", {"state": "FOREGROUND"}, user="hh-real")]
    tables = mod.analyse(redirects, debug, CONFIG)
    daily = tables["daily"][0]
    assert (daily["redirect_rows"], daily["guest_ids"]) == (3, 2) and "not real households" in daily["note"]
    total = next(r for r in tables["periods"] if r["period"] == "all")
    assert total["rows_ending_journey"] == 2 and total["guests_also_non_guest"] == 1
    assert total["non_guest_match_rate"] == pytest.approx(0.5)


def test_non_guest_match_not_measurable_without_non_guest_ids():
    tables = mod.analyse([_redirect("g1", "2026-11-05 03:00:00.000")], [_discovery("g1", "2026-11-05T02:00:00.000Z", NEW)],
                         CONFIG)
    assert next(r for r in tables["periods"] if r["period"] == "all")["non_guest_match_rate"] == "not_measurable"


def test_preceding_events_flag_6001_and_webview():
    redirects = [_redirect("g1", "2026-11-05 03:00:10.000")]
    debug = [_discovery("g1", "2026-11-05T02:59:00.000Z", NEW, ua=WEBVIEW_UA),
             _debug("g1", "2026-11-05T03:00:05.000Z", "APP_ERROR", {"errorcode": "6001"}),
             _debug("g1", "2026-11-05T03:00:10.000Z", "ACTION_SCREEN_CHANGE", {"screenname": mod.REDIRECT_SCREEN})]
    tables = mod.analyse(redirects, debug, CONFIG)
    total = next(r for r in tables["periods"] if r["period"] == "all")
    assert total["guests_6001_before_redirect"] == 1 and total["guests_webview_ua"] == 1
    labels = {r["preceding_event"] for r in tables["preceding"]}
    assert "APP_ERROR" in labels and not any(mod.REDIRECT_SCREEN in label for label in labels)


def test_missing_column_fails_loudly():
    with pytest.raises(mod.GuestRedirectError):
        mod.analyse([{"user_id": "GUEST.x"}], [], CONFIG)


def test_main_idempotent_and_missing_data(tmp_path, capsys):
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir()
    day = "2026-11-05"
    fields = list(_redirect("g1", "x"))
    with open(data / f"{day}_guest_login_redirect.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(_redirect("g1", "2026-11-05 03:00:00.000"))
    with open(data / f"{day}_guest_redirect_debug_events.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(_debug("g1", "t", "e", {})))
        writer.writeheader()
        writer.writerow(_discovery("g1", "2026-11-05T02:00:00.000Z", NEW))
    args = ["--start-date", day, "--end-date", day, "--data-dir", str(data), "--output-dir", str(out)]
    assert mod.main(args) == 0 and mod.main(args) == 0
    assert len(list(out.glob("*_guest_redirect_*.csv"))) == 4
    assert "per-install" in capsys.readouterr().out
    assert mod.main(["--start-date", "2026-11-02", "--end-date", "2026-11-02", "--data-dir", str(data),
                     "--output-dir", str(out)]) == 2
