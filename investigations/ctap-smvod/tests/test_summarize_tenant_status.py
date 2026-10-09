"""Tests for summarize_tenant_status.py."""
from __future__ import annotations

import csv
import sys

from conftest import load_script

mod = load_script("summarize_tenant_status.py")

COLS = list(mod.REQUIRED_COLUMNS)


def sess(sid, state="CREATE->BUFFERING->PLAYING", codes="", device="d1", outcome="DESTROY", moved="false",
         startup="4000", cls="Mobile"):
    return {"sessionId": sid, "deviceId": device, "householdId": "h1", "playback_outcome": outcome, "error_codes": codes,
            "state_sequence": state, "position_not_moved": moved, "startup_time_ms": startup, "Device Class": cls}


def write_report(root, tenant, iso, rows):
    d = root / "output" / tenant
    d.mkdir(parents=True)
    with (d / f"{iso}_setupsession_with_outcome.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def test_dedupe_sessions_keeps_first_and_drops_blank():
    rows = [sess("a"), sess("a", codes="1003"), sess(""), sess("b")]
    assert [r["sessionId"] for r in mod.dedupe_sessions(rows)] == ["a", "b"]


def test_error_codes_of_splits_and_handles_empty():
    assert mod.error_codes_of({"error_codes": "1003;E31012, 1003|6001"}) == {"1003", "E31012", "6001"}
    assert mod.error_codes_of({"error_codes": ""}) == set()


def test_percentile_interpolates_and_empty_is_none():
    assert mod.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert mod.percentile([], 0.5) is None


def test_tenant_metrics_played_ok_and_buckets():
    rows = [sess("a"), sess("a"), sess("b", state="CREATE->ERROR(1003)->DESTROY", codes="1003", outcome="PLAYER_ERROR"),
            sess("c", state="CREATE->BUFFERING->PLAYING->ERROR(3016)", codes="3016"),
            sess("d", state="CREATE->DESTROY", outcome="EBVS", moved="true")]
    m = mod.tenant_metrics(rows)
    assert (m["sessions"], m["ok"], m["errored"], m["neither"], m["errored_pre_play"]) == (4, 1, 2, 1, 1)
    assert m["pos_not_moved"] == 1 and m["codes"] == {"1003": 1, "3016": 1}


def test_tenant_metrics_empty_report_has_no_divide_error():
    m = mod.tenant_metrics([])
    assert m["sessions"] == 0 and m["startup_p50"] is None and m["main_class"] is None
    assert mod.pct(0, 0) == "n/a"


def test_render_omits_incomplete_no_destroy_and_shows_tenants():
    m = {"SA": mod.tenant_metrics([sess("a", outcome="INCOMPLETE_NO_DESTROY")]), "GH": mod.tenant_metrics([sess("b")])}
    out = mod.render("2026-10-08", m)
    assert "| SA | GH |" in out and "| DESTROY |" in out
    assert "| INCOMPLETE_NO_DESTROY" not in out


def test_main_writes_default_file_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    write_report(tmp_path, "SA", "2026-10-08", [sess("a")])
    monkeypatch.setattr(sys, "argv", ["x", "--date", "08102026", "--tenants", "SA", "--root", str(tmp_path)])
    assert mod.main() == 0
    assert (tmp_path / "docs" / "2026-10-08-tenant-status-summary.md").exists()
    assert mod.main() == 1 and "--force" in capsys.readouterr().err


def test_main_missing_tenant_file_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["x", "--date", "08102026", "--tenants", "ZM", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "ERROR" in capsys.readouterr().err


def test_main_missing_column_exits_nonzero(tmp_path, monkeypatch, capsys):
    d = tmp_path / "output" / "SA"
    d.mkdir(parents=True)
    (d / "2026-10-08_setupsession_with_outcome.csv").write_text("sessionId\na\n")
    monkeypatch.setattr(sys, "argv", ["x", "--date", "08102026", "--tenants", "SA", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "missing required column" in capsys.readouterr().err


def test_pct_half_percent_is_not_shown_as_zero():
    assert mod.pct(1, 200) == "<1%"
    assert mod.pct(0, 200) == "0%"
