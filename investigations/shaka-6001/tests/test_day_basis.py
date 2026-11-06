from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from scripts.lib.day_basis import DayBasis, DayBasisError, day_of, parse_utc

IST = ZoneInfo("Asia/Kolkata")


def test_evening_utc_is_next_day_in_ist():
    ts = parse_utc("2026-11-04T20:00:00.000Z")
    assert day_of(ts, DayBasis.IST, IST).isoformat() == "2026-11-05"
    assert day_of(ts, DayBasis.UTC, IST).isoformat() == "2026-11-04"


def test_naive_is_utc_and_bad_input_raises():
    assert parse_utc("2026-11-04T00:00:00").tzinfo == timezone.utc
    with pytest.raises(DayBasisError):
        parse_utc("nope")
    with pytest.raises(DayBasisError):
        day_of(datetime(2026, 11, 4), DayBasis.IST, IST)
