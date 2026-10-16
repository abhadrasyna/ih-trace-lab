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
    (tmp_path / "SA").mkdir()
    path = tmp_path / "SA" / f"{DAY}_setupsession_with_outcome.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["sessionId", "start_time"])
        w.writeheader()
        w.writerow(row("a", "2026-10-14 00:01:00.000 UTC"))
    with mock.patch.object(mod, "render_chart", side_effect=ChartError("boom")):
        assert mod.write_chart("SA", DAY, 5, tmp_path) is False
    assert path.exists() and not (tmp_path / "SA" / f"{DAY}_playback_attempts.png").exists()
    assert mod.write_chart("SA", DAY, 5, tmp_path) is True
