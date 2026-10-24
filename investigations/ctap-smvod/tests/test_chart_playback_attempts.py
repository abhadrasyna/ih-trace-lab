"""Tests for chart_playback_attempts.py (offline; renders to bytes only)."""
from __future__ import annotations

import csv
from datetime import date
from unittest import mock

import pytest

from conftest import load_script
from src.lib.charts.errors import ChartError

mod = load_script("chart_playback_attempts.py")
DAY = date(2026, 10, 14)


def row(sid: str, ts: str) -> dict[str, str]:
    return {"sessionId": sid, "start_time": ts}


def test_attempts_dedupe_sessions_and_bucket():
    rows = [row("a", "2026-10-14 00:01:00.000 UTC"), row("a", "2026-10-14 00:09:00.000 UTC"), row("b", "2026-10-14 00:06:00.000 UTC")]
    counts = mod.attempts_per_bucket(rows, DAY, 5)
    assert len(counts) == 288 and counts[0] == 1 and counts[1] == 1 and sum(counts) == 2


def test_attempts_ignore_other_days():
    assert sum(mod.attempts_per_bucket([row("a", "2026-10-13 23:59:00.000 UTC")], DAY, 5)) == 0


def test_attempts_bad_bucket_or_blank_row_raises():
    with pytest.raises(ValueError):
        mod.attempts_per_bucket([], DAY, 7)
    with pytest.raises(ValueError):
        mod.attempts_per_bucket([row("", "2026-10-14 00:00:00 UTC")], DAY, 5)


def test_render_chart_returns_png():
    counts = [i % 9 for i in range(288)]
    assert mod.render_chart(counts, "t", 5)[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_chart_bad_input_raises_chart_error():
    with pytest.raises(ChartError):
        mod.render_chart([], "t", 5)


def test_chart_failure_does_not_block_report(tmp_path):
    (tmp_path / "ZA").mkdir()
    path = tmp_path / "ZA" / f"{DAY}_setupsession_with_outcome.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["sessionId", "start_time"])
        w.writeheader()
        w.writerow(row("a", "2026-10-14 00:01:00.000 UTC"))
    with mock.patch.object(mod, "render_chart", side_effect=ChartError("boom")):
        assert mod.write_chart("ZA", DAY, 5, tmp_path) is False
    assert path.exists() and not (tmp_path / "ZA" / "charts" / f"{DAY}_playback_attempts.png").exists()
    assert mod.write_chart("ZA", DAY, 5, tmp_path) is True


def test_attempts_by_ingest_uses_earliest_ingest_per_session():
    rows = [
        {"sessionId": "a", "ingest_timestamp": "2026-10-14 00:11:00.000"},
        {"sessionId": "a", "ingest_timestamp": "2026-10-14 00:02:00.000"},
        {"sessionId": "b", "ingest_timestamp": "2026-10-15 00:02:00.000"},
    ]
    counts = mod.attempts_per_bucket(rows, DAY, 5, "ingest_timestamp")
    assert counts[0] == 1 and sum(counts) == 1


def test_read_rows_missing_ingest_column_raises(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("sessionId,event_start\na,2026-10-14 00:00:00\n")
    with pytest.raises(ValueError):
        mod.read_rows(path, "ingest_timestamp")


def test_write_chart_bad_time_field_raises(tmp_path):
    with pytest.raises(ValueError):
        mod.write_chart("ZA", DAY, 5, tmp_path, "ingest_timestamp", tmp_path)


def test_write_chart_ingest_mode(tmp_path):
    (tmp_path / "data" / "ZA").mkdir(parents=True)
    (tmp_path / "out" / "ZA").mkdir(parents=True)
    (tmp_path / "data" / "ZA" / f"{DAY}_session_ingest.csv").write_text(
        "sessionId,event_start,ingest_timestamp\na,2026-10-14 00:01:00,2026-10-14 00:10:00\nb,2026-10-14 23:59:00,2026-10-15 01:00:00\n")
    assert mod.write_chart("ZA", DAY, 5, tmp_path / "out", "ingest", tmp_path / "data") is True
    assert (tmp_path / "out" / "ZA" / "charts" / f"{DAY}_playback_attempts_ingest.png").exists()


def test_late_arrivals_counts_only_day_sessions_ingested_elsewhere():
    rows = [
        {"sessionId": "a", "event_start": "2026-10-14 23:00:00", "ingest_timestamp": "2026-10-15 01:00:00"},
        {"sessionId": "b", "event_start": "2026-10-14 10:00:00", "ingest_timestamp": "2026-10-14 10:05:00"},
        {"sessionId": "c", "event_start": "2026-10-13 23:00:00", "ingest_timestamp": "2026-10-13 23:05:00"},
    ]
    assert mod.late_arrivals(rows, DAY) == 1
