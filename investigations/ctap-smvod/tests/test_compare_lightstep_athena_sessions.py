"""Tests for compare_lightstep_athena_sessions.py (offline)."""
from __future__ import annotations

import pytest

from conftest import load_script

mod = load_script("compare_lightstep_athena_sessions.py")


def test_unique_ids_dedupes_and_counts_blank():
    ids, blank = mod.unique_ids([{"sessionId": "a"}, {"sessionId": "a"}, {"sessionId": " "}, {"sessionId": "b"}])
    assert ids == {"a", "b"} and blank == 1


def test_diff_sets_partitions():
    parts = mod.diff_sets({"a", "b"}, {"b", "c"})
    assert parts == {"both": {"b"}, "lightstep_only": {"a"}, "athena_only": {"c"}}


def test_mismatch_rows_enrich_and_classify():
    parts = mod.diff_sets({"a", "z"}, {"c"})
    ingest = {"a": {"event_start": "e", "ingest_timestamp": "i"}, "c": {"event_start": "e2", "ingest_timestamp": "i2"}}
    rows = {r["sessionId"]: r for r in mod.mismatch_rows(parts, {"a": "t"}, ingest, True)}
    assert rows["a"]["athena_elsewhere"] == "athena_d_minus_1" and rows["a"]["lightstep_start_time"] == "t"
    assert rows["z"]["athena_elsewhere"] == "not_in_athena_d_or_d_minus_1"
    assert rows["c"]["athena_ingest_timestamp"] == "i2" and rows["c"]["athena_elsewhere"] == ""


def test_earliest_start_picks_min():
    rows = [{"sessionId": "a", "start_time": "2026-10-14 02:00"}, {"sessionId": "a", "start_time": "2026-10-14 01:00"}, {"sessionId": "b", "start_time": ""}]
    assert mod.earliest_start(rows) == {"a": "2026-10-14 01:00"}


def test_index_ingest_duplicate_raises():
    assert mod.index_ingest([{"sessionId": "a"}]) == {"a": {"sessionId": "a"}}
    with pytest.raises(ValueError):
        mod.index_ingest([{"sessionId": "a"}, {"sessionId": "a"}])


def test_read_rows_missing_column_raises(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        mod.read_rows(p, ["sessionId"])
    with pytest.raises(FileNotFoundError):
        mod.read_rows(tmp_path / "nope.csv", ["a"])
