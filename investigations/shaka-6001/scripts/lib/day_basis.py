"""Assign a UTC timestamp to a calendar day on a chosen basis (IST by default). Shared by SU-12 and SU-13."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo


class DayBasis(str, Enum):
    IST = "ist"
    UTC = "utc"


class DayBasisError(Exception):
    """A timestamp cannot be parsed or assigned to a day."""


def parse_utc(text: str) -> datetime:
    """Parse an ISO-8601 table timestamp (``...Z`` or offset); naive values are taken as UTC."""
    value = (text or "").strip()
    if not value:
        raise DayBasisError("empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DayBasisError(f"unparseable timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def day_of(ts_utc: datetime, basis: DayBasis, local_tz: ZoneInfo) -> date:
    """UTC instant to its calendar day: the UTC date, or the date in ``local_tz`` (IST) for ``DayBasis.IST``."""
    if ts_utc.tzinfo is None:
        raise DayBasisError("ts_utc must be timezone-aware")
    if basis is DayBasis.UTC:
        return ts_utc.astimezone(timezone.utc).date()
    return ts_utc.astimezone(local_tz).date()
