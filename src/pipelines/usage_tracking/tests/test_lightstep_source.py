"""Tests for the Lightstep request source (no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.pipelines.usage_tracking.errors import LightstepSourceError, UsageTrackingError
from src.pipelines.usage_tracking.lightstep_source import LiveLightstepSource, LocalExportSource, RequestRow, request_counts
from src.pipelines.usage_tracking.roster import Household, Member

DAY = date(2026, 11, 2)
HH = Household(hhid="H1", label="team", tenant="ZA", track=True, members=(Member("Sai", "d1"), Member("Fayaz", "d2")), phone="1")
HEADER = '"householdId","deviceId","session.clientIp","sessionId","contentId","externalPackageId","lightstep.trace_id","playbackURL","min","max","avg","sum","value"\n'


def _line(hh: str, dev: str, sid: str, trace: str, total: str = "1") -> str:
    return f'"{hh}","{dev}","1.1.1.1","{sid}","c","p","{trace}","u","1","1","1","{total}",""\n'


def _export(tmp_path: Path, body: str) -> Path:
    folder = tmp_path / "ZA"
    folder.mkdir()
    (folder / f"{DAY}_smvod.csv").write_text("\ufeff" + HEADER + body, encoding="utf-8")
    return tmp_path


def test_counts_per_device(tmp_path):
    body = _line("H1", "d1", "s1", "t1") + _line("H1", "d1", "s2", "t2", "2") + _line("H1", "d9", "s3", "t3") + _line("OTHER", "d1", "s4", "t4")
    rows = LocalExportSource("ZA", _export(tmp_path, body)).fetch_requests([HH], DAY)
    assert [r.trace_id for r in rows] == ["t1", "t2"]
    assert request_counts(rows, [HH]) == {("H1", "d1"): 3, ("H1", "d2"): 0}


def test_missing_export_raises(tmp_path):
    with pytest.raises(LightstepSourceError, match="missing") as info:
        LocalExportSource("ZA", tmp_path).fetch_requests([HH], DAY)
    assert isinstance(info.value, UsageTrackingError)


def test_absent_device_is_zero_not_error(tmp_path):
    rows = LocalExportSource("ZA", _export(tmp_path, "")).fetch_requests([HH], DAY)
    assert rows == []
    assert request_counts(rows, [HH]) == {("H1", "d1"): 0, ("H1", "d2"): 0}


def test_malformed_export_row_raises(tmp_path):
    with pytest.raises(LightstepSourceError, match="malformed"):
        LocalExportSource("ZA", _export(tmp_path, _line("H1", "d1", "s1", "t1", "many"))).fetch_requests([HH], DAY)


def test_live_query_keeps_pairs_together_and_parses_series():
    seen: list[str] = []
    days: list[date] = []

    def run(uql: str, day: date):
        seen.append(uql)
        days.append(day)
        labels = ["householdId=H1", "deviceId=d1", "sessionId=s1", "lightstep.trace_id=t1"]
        return [{"group-labels": labels, "points": [[0, 1.0], [1, 2.0]]}]

    rows = LiveLightstepSource("ZA", run, tenant_filter=' && busUnitId == "g"').fetch_requests([HH], DAY)
    assert rows == [RequestRow("s1", "H1", "d1", "t1", 3)]
    assert '(householdId == "H1" && deviceId == "d1") || (householdId == "H1" && deviceId == "d2")' in seen[0]
    assert days == [DAY]
    assert 'busUnitId == "g"' in seen[0] and "{{" not in seen[0]


def test_live_api_error_is_wrapped():
    def boom(uql: str, day: date):
        raise RuntimeError("503")

    with pytest.raises(LightstepSourceError, match="503"):
        LiveLightstepSource("ZA", boom).fetch_requests([HH], DAY)


def test_fractional_live_count_raises():
    def run(uql: str, day: date):
        return [{"group-labels": ["householdId=H1", "deviceId=d1", "sessionId=s1", "lightstep.trace_id=t1"], "points": [[0, 1.5]]}]

    with pytest.raises(LightstepSourceError, match="malformed"):
        LiveLightstepSource("ZA", run).fetch_requests([HH], DAY)


def test_live_rows_outside_roster_are_dropped():
    def run(uql: str, day: date):
        return [{"group-labels": ["householdId=OTHER", "deviceId=d1", "sessionId=s1", "lightstep.trace_id=t1"], "points": [[0, 1.0]]}]

    assert LiveLightstepSource("ZA", run).fetch_requests([HH], DAY) == []


def test_live_query_without_pairs_placeholder_raises(tmp_path):
    bad = tmp_path / "q.md"
    bad.write_text("```\nspans count\n```\n")
    with pytest.raises(LightstepSourceError, match="placeholder"):
        LiveLightstepSource("ZA", lambda u, d: [], query_file=bad).fetch_requests([HH], DAY)


def test_live_query_without_tenant_placeholder_raises(tmp_path):
    bad = tmp_path / "q.md"
    bad.write_text("```\nspans count && ({{pairs_filter}})\n```\n")
    with pytest.raises(LightstepSourceError, match="shared-project"):
        LiveLightstepSource("ZA", lambda u, d: [], tenant_filter=" && busUnitId == 'g'", query_file=bad).fetch_requests([HH], DAY)


def test_tenant_mismatch_raises(tmp_path):
    other = Household(hhid="H9", label="x", tenant="GH", track=True, members=(), phone=None)
    with pytest.raises(LightstepSourceError, match="tenant"):
        LocalExportSource("ZA", tmp_path).fetch_requests([other], DAY)
