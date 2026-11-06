import csv
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts import rank_daily_top_impacted as mod
from scripts.lib.day_basis import DayBasis

IST = ZoneInfo("Asia/Kolkata")
D = date(2026, 11, 4)


def ev(ts, hh="h1", dev="d1", sess="s1", model="P11", **kw):
    row = {"datetime": ts, "household_id": hh, "device_id": dev, "session_id": sess, "device_model": model,
           "build_id": "B1", "is_webview": "True", "period": "before", "app_version": "v1"}
    return row | kw


def tables(rows, basis=DayBasis.IST, top=10, start=D, end=date(2026, 11, 5)):
    by_day = mod.assign_days(rows, basis, IST, start, end)
    return mod.build_tables(by_day, top, IST, "ZA", basis)


def test_top_n_per_day_with_stable_ties():
    rows = [ev("2026-11-04T05:00:00Z", hh="b", sess="s1"), ev("2026-11-04T05:01:00Z", hh="b", sess="s1"),
            ev("2026-11-04T05:02:00Z", hh="a", sess="s2"), ev("2026-11-04T05:03:00Z", hh="a", sess="s3"),
            ev("2026-11-04T05:04:00Z", hh="c", sess="s4"), ev("2026-11-04T05:05:00Z", hh="c", sess="s4"),
            ev("2026-11-04T05:06:00Z", hh="z", sess="s9")]
    out, _ = tables(rows, top=3)
    ids = [(r["rank"], r["id"], r["events_6001"], r["distinct_sessions"]) for r in out["households"]]
    # a has 2 sessions so wins the 2-event tie; b and c tie fully and fall back to id
    assert ids == [(1, "a", 2, 2), (2, "b", 2, 1), (3, "c", 2, 1)]
    assert out["households"][0]["top_share_pct"] == round(100 * 6 / 7, 2)


def test_guest_ids_ranked_separately():
    rows = [ev("2026-11-04T05:00:00Z", dev="GUEST.x"), ev("2026-11-04T05:01:00Z", dev="GUEST.x"),
            ev("2026-11-04T05:02:00Z", dev="real"), ev("2026-11-04T05:03:00Z", dev="", hh="")]
    out, unassigned = tables(rows)
    assert [r["id"] for r in out["devices"]] == ["real"]
    assert [r["id"] for r in out["guest_devices"]] == ["GUEST.x"]
    row = next(u for u in unassigned if u["kind"] == "devices")
    assert (row["events_without_id"], row["day_events"]) == (1, 4)


def test_day_basis_ist_vs_utc():
    rows = [ev("2026-11-04T20:00:00Z")]
    ist, _ = tables(rows, DayBasis.IST)
    utc, _ = tables(rows, DayBasis.UTC)
    assert ist["devices"][0]["day"] == "2026-11-05"
    assert ist["devices"][0]["first_6001_ist"].startswith("2026-11-05T01:30:00+05:30")
    assert utc["devices"][0]["day"] == "2026-11-04"


def test_bad_timestamp_and_missing_columns_raise():
    with pytest.raises(mod.RankImpactedError):
        mod.assign_days([ev("garbage")], DayBasis.IST, IST, D, D)
    with pytest.raises(mod.RankImpactedError):
        mod.validate([{"datetime": "x"}])


def test_main_writes_csvs_and_is_idempotent(tmp_path: Path):
    src = tmp_path / "in.csv"
    rows = [ev("2026-11-04T05:00:00Z"), ev("2026-11-04T05:01:00Z", dev="GUEST.g")]
    with src.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    argv = ["--start-date", "2026-11-04", "--end-date", "2026-11-04", "--input", str(src),
            "--output-dir", str(tmp_path / "out"), "--no-charts"]
    assert mod.main(argv) == 0
    assert mod.main(argv) == 0
    out = tmp_path / "out"
    names = sorted(p.name for p in out.iterdir())
    assert "2026-11-04_2026-11-04_6001_top10_households.csv" in names
    assert "2026-11-04_2026-11-04_6001_top10_devices.csv" in names
    assert not any(n.endswith(".tmp") for n in names)


def _members(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["device_id", "household_id", "status", "recovered", "never_recovered"])
        w.writeheader()
        w.writerows(rows)
    return path


def test_read_recovery_aggregates_members_per_id(tmp_path: Path):
    path = _members(tmp_path / "m.csv", [
        {"device_id": "d1", "household_id": "h1", "status": "ok", "recovered": "False", "never_recovered": "True"},
        {"device_id": "d2", "household_id": "h1", "status": "ok", "recovered": "True", "never_recovered": "False"},
        {"device_id": "d3", "household_id": "h2", "status": "no_session_rows", "recovered": "False",
         "never_recovered": "False"},
    ])
    flags = mod.read_recovery(path)
    assert flags["household_id"] == {"h1": "recovered"}  # any recovered member wins; unscored h2 has no flag
    assert flags["device_id"] == {"d1": "never_recovered", "d2": "recovered"}
    assert mod.read_recovery(tmp_path / "absent.csv") == {} and mod.read_recovery(None) == {}
    bad = _members(tmp_path / "bad.csv", [])
    bad.write_text("id,never_recovered\nx,True\n")
    with pytest.raises(mod.RankImpactedError):
        mod.read_recovery(bad)


def test_main_fills_recovery_flag_from_members_file(tmp_path: Path):
    src = tmp_path / "in.csv"
    rows = [ev("2026-11-04T05:00:00Z"), ev("2026-11-04T05:01:00Z", dev="d2", hh="h2")]
    with src.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    out = tmp_path / "out"
    flags = {"device_id": "d1", "household_id": "h1", "status": "ok", "recovered": "True", "never_recovered": "False"}
    out.mkdir()
    members = tmp_path / "members.csv"
    _members(members, [flags])
    argv = ["--start-date", "2026-11-04", "--end-date", "2026-11-04", "--input", str(src),
            "--output-dir", str(out), "--no-charts", "--recovery-csv", str(members)]
    assert mod.main(argv) == 0
    devices = list(csv.DictReader((out / "2026-11-04_2026-11-04_6001_top10_devices.csv").open()))
    assert {r["id"]: r["recovery_flag"] for r in devices} == {"d1": "recovered", "d2": ""}
