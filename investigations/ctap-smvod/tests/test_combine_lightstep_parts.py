"""Tests for combine_lightstep_parts.py (split-export recombination)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from conftest import load_script

combine_lightstep_parts = load_script("combine_lightstep_parts.py")


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_combines_numbered_parts_with_different_column_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Part 1 uses the "normal" column order; part 2 has the same columns
    # shuffled -- this is the real shape seen in a 2026-10-03 smvod-ts
    # re-download and must still merge correctly by column name.
    _write_csv(
        tmp_path / "2026-10-03_01_smvod-ts.csv",
        ["sessionId", "contentId", "duration_millis"],
        [["s1", "c1", "100"], ["s2", "c2", "200"]],
    )
    _write_csv(
        tmp_path / "2026-10-03_02_smvod-ts.csv",
        ["contentId", "duration_millis", "sessionId"],
        [["c3", "300", "s3"]],
    )
    monkeypatch.setattr(
        sys, "argv", ["combine_lightstep_parts.py", "--input-dir", str(tmp_path)]
    )
    monkeypatch.setattr(combine_lightstep_parts, "init_logging", Mock())

    combine_lightstep_parts.main()

    out_path = tmp_path / "2026-10-03_smvod-ts.csv"
    assert out_path.exists()
    with out_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["sessionId"] for r in rows] == ["s1", "s2", "s3"]
    assert [r["contentId"] for r in rows] == ["c1", "c2", "c3"]
    assert [r["duration_millis"] for r in rows] == ["100", "200", "300"]
    out = capsys.readouterr().out
    assert "Combined 2026-10-03_smvod-ts parts ['01', '02'] (3 rows)" in out


def test_leaves_non_numbered_day_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    whole_file = tmp_path / "2026-09-28_ctap.csv"
    _write_csv(whole_file, ["lightstep.trace_id"], [["t1"]])
    original_mtime = whole_file.stat().st_mtime

    monkeypatch.setattr(
        sys, "argv", ["combine_lightstep_parts.py", "--input-dir", str(tmp_path)]
    )
    monkeypatch.setattr(combine_lightstep_parts, "init_logging", Mock())

    combine_lightstep_parts.main()

    assert whole_file.stat().st_mtime == original_mtime
    with whole_file.open(newline="") as f:
        assert list(csv.DictReader(f)) == [{"lightstep.trace_id": "t1"}]


def test_raises_on_mismatched_column_sets(tmp_path: Path) -> None:
    part1 = tmp_path / "2026-10-03_01_ctap.csv"
    part2 = tmp_path / "2026-10-03_02_ctap.csv"
    _write_csv(part1, ["lightstep.trace_id", "value"], [["t1", "1"]])
    _write_csv(part2, ["lightstep.trace_id", "extra_col"], [["t2", "x"]])

    with pytest.raises(combine_lightstep_parts.ColumnMismatchError) as exc_info:
        combine_lightstep_parts.combine_parts([str(part1), str(part2)])

    assert "extra_col" in str(exc_info.value)


def test_rebuilds_a_combined_file_this_script_previously_produced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # run_pipeline.py's Step 1b re-invokes this script on every pipeline run,
    # unconditionally. A combined file *this script produced* (tracked via its
    # sidecar manifest) must always reflect the parts currently on disk -- not
    # whatever was combined on a previous run -- so this never relies on
    # mtimes (which can't reliably detect a deleted part, a re-copied part
    # with its original timestamp preserved, or a same-second filesystem
    # mtime collision).
    part1 = tmp_path / "2026-10-03_01_ctap.csv"
    part2 = tmp_path / "2026-10-03_02_ctap.csv"
    _write_csv(part1, ["lightstep.trace_id"], [["t1"]])
    _write_csv(part2, ["lightstep.trace_id"], [["t2"]])
    existing = tmp_path / "2026-10-03_ctap.csv"
    _write_csv(existing, ["lightstep.trace_id"], [["stale"]])  # written last -> newest mtime
    (tmp_path / "2026-10-03_ctap.csv.combined-from.json").write_text(
        '{"parts": ["2026-10-03_01_ctap.csv", "2026-10-03_02_ctap.csv"]}'
    )

    monkeypatch.setattr(
        sys, "argv", ["combine_lightstep_parts.py", "--input-dir", str(tmp_path)]
    )
    monkeypatch.setattr(combine_lightstep_parts, "init_logging", Mock())

    combine_lightstep_parts.main()

    with existing.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"lightstep.trace_id": "t1"}, {"lightstep.trace_id": "t2"}]
    assert "Combined 2026-10-03_ctap" in capsys.readouterr().out


def test_refuses_to_overwrite_a_combined_file_without_a_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A YYYY-MM-DD_<artifact>.csv that exists but has no sidecar manifest wasn't
    # produced by this script -- e.g. a manually exported whole-day file that
    # happens to share a date with some stray numbered parts. It must never be
    # silently overwritten.
    part1 = tmp_path / "2026-10-03_01_ctap.csv"
    part2 = tmp_path / "2026-10-03_02_ctap.csv"
    _write_csv(part1, ["lightstep.trace_id"], [["t1"]])
    _write_csv(part2, ["lightstep.trace_id"], [["t2"]])
    existing = tmp_path / "2026-10-03_ctap.csv"
    _write_csv(existing, ["lightstep.trace_id"], [["manually-exported-whole-day"]])

    monkeypatch.setattr(
        sys, "argv", ["combine_lightstep_parts.py", "--input-dir", str(tmp_path)]
    )
    monkeypatch.setattr(combine_lightstep_parts, "init_logging", Mock())

    with pytest.raises(combine_lightstep_parts.UnmanagedCombinedFileError):
        combine_lightstep_parts.main()

    with existing.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"lightstep.trace_id": "manually-exported-whole-day"}]

