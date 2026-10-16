"""Tests for lib/concurrency.py and compute_concurrent_playback.py."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from conftest import load_script
from lib import concurrency as cc

mod = load_script("compute_concurrent_playback.py")
DAY = date(2026, 10, 14)


def ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 10, 14, h, m, s, tzinfo=timezone.utc)


def test_parse_ts_handles_all_three_formats():
    expected = ts(1, 39, 23).replace(microsecond=892000)
    assert cc.parse_ts("2026-10-14 01:39:23.892 UTC") == expected
    assert cc.parse_ts("2026-10-14 01:39:23.892") == expected
    assert cc.parse_ts("2026-10-14T01:39:23.892Z") == expected


def test_parse_ts_empty_raises():
    with pytest.raises(ValueError):
        cc.parse_ts("  ")


def test_per_minute_concurrency_overlap_and_clipping():
    counts = cc.per_minute_concurrency([(ts(0, 0), ts(0, 2, 30)), (ts(0, 1), ts(0, 1, 10))], DAY)
    assert counts[:4] == [1, 2, 1, 0]
    prev_day = datetime(2026, 10, 13, 23, 59, tzinfo=timezone.utc)
    assert cc.per_minute_concurrency([(prev_day, ts(0, 0, 30))], DAY)[:2] == [1, 0]
    assert cc.per_minute_concurrency([(prev_day, prev_day)], DAY) == [0] * 1440


def test_peak_returns_first_max_and_rejects_empty():
    assert cc.peak([1, 3, 3, 2]) == (3, 1)
    with pytest.raises(ValueError):
        cc.peak([])


def test_intervals_skip_no_end_and_reject_reversed_or_blank_id():
    rows = [
        {"sessionId": "a", "event_start": "2026-10-14 01:00:00", "event_end": "2026-10-14 01:05:00"},
        {"sessionId": "b", "event_start": "2026-10-14 01:00:00", "event_end": ""},
        {"sessionId": "", "event_start": "", "event_end": ""},
    ]
    out, skipped = cc.intervals_from_session_rows(rows)
    assert list(out) == ["a"] and skipped == 2
    with pytest.raises(ValueError):
        cc.intervals_from_session_rows([{"sessionId": "c", "event_start": "2026-10-14 02:00:00", "event_end": "2026-10-14 01:00:00"}])
    with pytest.raises(ValueError):
        cc.intervals_from_session_rows([{"sessionId": "", "event_start": "2026-10-14 01:00:00", "event_end": "2026-10-14 01:01:00"}])


def test_merge_with_estimates_counts_estimated_and_unresolved():
    exact = {"a": (ts(1, 0), ts(1, 1))}
    spans = {"b": (ts(2, 0), ts(2, 9))}
    merged, est, unres = cc.merge_with_estimates(exact, ["a", "b", "b", "c"], spans)
    assert set(merged) == {"a", "b"} and (est, unres) == (1, 1)


def test_debug_spans_min_max_and_blank_raises():
    rows = [{"sessionId": "a", "datetime": "2026-10-14T01:00:05.000Z"}, {"sessionId": "a", "datetime": "2026-10-14T01:00:01.000Z"}]
    assert cc.debug_spans(rows)["a"] == (ts(1, 0, 1), ts(1, 0, 5))
    with pytest.raises(ValueError):
        cc.debug_spans([{"sessionId": "a", "datetime": ""}])


def test_build_views_estimated_exceeds_exact():
    outcome = [{"sessionId": "a", "event_start": "2026-10-14 01:00:00", "event_end": "2026-10-14 01:02:00"}]
    sessions = outcome + [{"sessionId": "b", "event_start": "", "event_end": ""}]
    debug = [{"sessionId": "b", "datetime": "2026-10-14T01:00:00Z"}, {"sessionId": "b", "datetime": "2026-10-14T01:01:00Z"}]
    series, summary = mod.build_views(outcome, sessions, debug, DAY)
    assert max(series["athena_exact"]) == 1 and max(series["athena_estimated"]) == 2
    assert summary[2][:6] == ["athena_estimated", 2, 1, 1, 0, 2]


def test_read_rows_missing_file_and_column(tmp_path):
    with pytest.raises(FileNotFoundError):
        mod.read_rows(tmp_path / "nope.csv", {"sessionId"})
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        mod.read_rows(p, {"sessionId"})
