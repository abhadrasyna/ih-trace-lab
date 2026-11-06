"""Load and validate ``config/analysis.yaml`` into a frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

DEFAULT_MAX_SCAN_GB = 10.0
DEFAULT_LOOKBACK_DAYS = 3
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "analysis.yaml"


class AnalysisConfigError(Exception):
    """Raised when analysis.yaml is missing, unreadable or invalid."""


@dataclass(frozen=True)
class AnalysisConfig:
    tenant: str
    default_start_date: date
    version_before: str
    version_after: str
    timezone: ZoneInfo
    window_start: datetime
    window_end: datetime
    max_scan_gb: float = DEFAULT_MAX_SCAN_GB
    daily_lookback_days: int = DEFAULT_LOOKBACK_DAYS


def _require(mapping: Any, key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping or mapping[key] in (None, ""):
        raise AnalysisConfigError(f"missing config key: {where}{key}")
    return mapping[key]


def _require_str(mapping: Any, key: str, where: str) -> str:
    value = _require(mapping, key, where)
    if not isinstance(value, str):
        raise AnalysisConfigError(f"{where}{key} must be a quoted string, got {value!r}")
    return value


def _parse_aware(value: Any, where: str) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AnalysisConfigError(f"invalid datetime for {where}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise AnalysisConfigError(f"{where} must carry a UTC offset: {value!r}")
    return parsed


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise AnalysisConfigError(f"invalid default_start_date: {value!r}") from exc


def _positive_number(raw: Any, key: str, default: float, *, integer: bool = False) -> float:
    if not isinstance(raw, dict) or key not in raw:
        return default
    value = raw[key]
    ok = isinstance(value, int) if integer else isinstance(value, (int, float))
    if isinstance(value, bool) or not ok or value <= 0:
        kind = "a positive integer" if integer else "a positive number"
        raise AnalysisConfigError(f"{key} must be {kind}, got {value!r}")
    return value


def parse_config(raw: Any) -> AnalysisConfig:
    """Validate an already-loaded mapping; pure, no I/O."""
    versions = _require(raw, "app_version", "")
    window = _require(raw, "upgrade_window", "")
    tz_name = _require_str(window, "timezone", "upgrade_window.")
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AnalysisConfigError(f"unknown timezone: {tz_name!r}") from exc
    start = _parse_aware(_require(window, "start", "upgrade_window."), "upgrade_window.start")
    end = _parse_aware(_require(window, "end", "upgrade_window."), "upgrade_window.end")
    if start >= end:
        raise AnalysisConfigError("upgrade_window.start must be before upgrade_window.end")
    before = _require_str(versions, "before", "app_version.")
    after = _require_str(versions, "after", "app_version.")
    if before == after:
        raise AnalysisConfigError("app_version.before and app_version.after must differ")
    return AnalysisConfig(
        tenant=_require_str(raw, "tenant", ""),
        default_start_date=_parse_date(_require(raw, "default_start_date", "")),
        version_before=before,
        version_after=after,
        timezone=tz,
        window_start=start.astimezone(tz),
        window_end=end.astimezone(tz),
        max_scan_gb=float(_positive_number(raw, "max_scan_gb", DEFAULT_MAX_SCAN_GB)),
        daily_lookback_days=int(_positive_number(raw, "daily_lookback_days", DEFAULT_LOOKBACK_DAYS, integer=True)),
    )


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AnalysisConfig:
    """Read and validate the YAML file; yaml/OS errors surface as AnalysisConfigError."""
    try:
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise AnalysisConfigError(f"cannot read config {path}: {exc}") from exc
    return parse_config(raw)
