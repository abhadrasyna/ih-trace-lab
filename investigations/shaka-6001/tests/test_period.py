"""Offline tests for the config loader and before/after classifier."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scripts.lib.analysis_config import AnalysisConfigError, load_config, parse_config
from scripts.lib.period import Period, classify_period

IST = timezone(timedelta(hours=5, minutes=30))
RAW = {
    "tenant": "ZA",
    "default_start_date": "2026-11-01",
    "app_version": {"before": "v-old", "after": "v-new"},
    "upgrade_window": {"timezone": "Asia/Kolkata", "start": "2026-11-04T16:30:00+05:30",
                       "end": "2026-11-04T17:00:00+05:30"},
}
CONFIG = parse_config(RAW)
BEFORE_V, AFTER_V = "v-old", "v-new"


def _utc(hour: int, minute: int) -> datetime:
    return datetime(2026, 11, 4, hour, minute, tzinfo=IST).astimezone(timezone.utc)


def test_classifies_before_and_after_by_timestamp():
    assert classify_period(_utc(16, 29), None, CONFIG) == (Period.BEFORE, False)
    assert classify_period(_utc(17, 1), None, CONFIG) == (Period.AFTER, False)
    assert classify_period(_utc(16, 29), BEFORE_V, CONFIG) == (Period.BEFORE, False)


def test_version_wins_outside_window_and_flags_conflict():
    assert classify_period(_utc(16, 29), AFTER_V, CONFIG) == (Period.AFTER, True)
    assert classify_period(_utc(17, 1), BEFORE_V, CONFIG) == (Period.BEFORE, True)


def test_window_uses_version_only():
    ts = _utc(16, 45)
    assert classify_period(ts, BEFORE_V, CONFIG) == (Period.BEFORE, False)
    assert classify_period(ts, AFTER_V, CONFIG) == (Period.AFTER, False)
    assert classify_period(ts, "v0.0.0", CONFIG) == (Period.UNKNOWN, False)
    assert classify_period(ts, None, CONFIG) == (Period.UNKNOWN, False)


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        classify_period(datetime(2026, 11, 4, 11, 0), None, CONFIG)


@pytest.mark.parametrize("drop", ["tenant", "app_version", "upgrade_window"])
def test_missing_config_key_raises(drop):
    raw = dict(RAW)
    del raw[drop]
    with pytest.raises(AnalysisConfigError):
        parse_config(raw)


def test_unreadable_config_raises(tmp_path):
    with pytest.raises(AnalysisConfigError):
        load_config(tmp_path / "nope.yaml")


def test_window_edges_are_inside_window():
    assert classify_period(_utc(16, 30), None, CONFIG).period is Period.UNKNOWN
    assert classify_period(_utc(17, 0), None, CONFIG).period is Period.UNKNOWN


def test_unquoted_numeric_version_raises():
    raw = {**RAW, "app_version": {"before": 3.10, "after": "v-new"}}
    with pytest.raises(AnalysisConfigError):
        parse_config(raw)


def test_real_config_loads():
    assert load_config().tenant == "ZA"
