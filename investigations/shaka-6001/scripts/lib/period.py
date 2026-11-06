"""Classify a row as before/after the ZA app upgrade."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import NamedTuple

from scripts.lib.analysis_config import AnalysisConfig


class Period(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    UNKNOWN = "unknown"


class PeriodResult(NamedTuple):
    period: Period
    conflict: bool  # timestamp and app version disagree outside the window


def _by_timestamp(ts: datetime, config: AnalysisConfig) -> Period | None:
    if ts < config.window_start:
        return Period.BEFORE
    if ts > config.window_end:
        return Period.AFTER
    return None


def _by_version(app_version: str | None, config: AnalysisConfig) -> Period:
    if app_version == config.version_before:
        return Period.BEFORE
    if app_version == config.version_after:
        return Period.AFTER
    return Period.UNKNOWN


def classify_period(ts_utc: datetime, app_version: str | None, config: AnalysisConfig) -> PeriodResult:
    """Version wins over timestamp; inside the window only the version decides."""
    if ts_utc.tzinfo is None:
        raise ValueError("ts_utc must be timezone-aware (UTC)")
    ts = ts_utc.astimezone(timezone.utc).astimezone(config.timezone)
    by_ts = _by_timestamp(ts, config)
    by_version = _by_version(app_version, config)
    if by_ts is None:
        return PeriodResult(by_version, False)
    if by_version is Period.UNKNOWN:
        return PeriodResult(by_ts, False)
    return PeriodResult(by_version, by_version is not by_ts)
