from scripts.lib import lightstep_smvod_ts as ts

COLUMNS = ("error_flag", "sessionId", "oldest_micros", "youngest_micros")


def test_derive_rows_uses_first_and_last_nonzero_point():
    series = [{"group-labels": ["sessionId=s1"], "points": [[1000, 0], [2000, 1], [5000, 3], [6000, 0]]}]
    assert ts.derive_rows(series, COLUMNS) == [list(COLUMNS), ["", "s1", "2000000", "5000000"]]


def test_series_without_nonzero_points_is_dropped():
    series = [{"group-labels": ["sessionId=s1"], "points": [[1000, 0]]}]
    assert ts.derive_rows(series, COLUMNS) == [list(COLUMNS)]
