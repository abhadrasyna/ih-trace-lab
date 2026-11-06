from datetime import datetime, timezone

import pytest

from scripts.probe_lightstep_slice import slice_window


def test_slice_window_is_utc_and_spans_minutes():
    oldest, youngest = slice_window("2026-10-31T10:00:00", 10)
    assert oldest == datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    assert youngest == datetime(2026, 10, 31, 10, 10, tzinfo=timezone.utc)


def test_slice_window_converts_an_explicit_offset_to_utc():
    oldest, _ = slice_window("2026-10-31T15:30:00+05:30", 5)
    assert oldest == datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)


def test_slice_window_rejects_non_positive_minutes():
    with pytest.raises(ValueError):
        slice_window("2026-10-31T10:00:00", 0)
