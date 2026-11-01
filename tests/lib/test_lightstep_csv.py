"""Offline tests for scripts/lib/lightstep_csv.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import lightstep_csv as lc

LRM_COLUMNS = ("fcId", "deviceId", "http.status_code", "min", "max", "avg", "sum", "value")

# Bytes taken from the shape of a hand-exported 2026-10-21_mdrm-lrm.csv: BOM, LF, all quoted, no trailing newline.
GOLDEN = (
    '\ufeff"fcId","deviceId","http.status_code","min","max","avg","sum","value"\n'
    '"6AD90789BAA1B529000214E9","dev-1","200","1","1","1","1",""'
)


def _series(**labels: str) -> dict[str, object]:
    return {"group-labels": [f"{k}={v}" for k, v in labels.items()], "points": [[1, 1]]}


def test_header_and_quoting_match_golden(tmp_path: Path) -> None:
    target = tmp_path / "2026-10-21_mdrm-lrm.csv"
    rows = lc.write_series_csv(
        target, [_series(fcId="6AD90789BAA1B529000214E9", deviceId="dev-1", **{"http.status_code": "200"})], LRM_COLUMNS
    )
    assert rows == 1
    assert target.read_bytes() == GOLDEN.encode("utf-8")


def test_existing_file_not_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "x.csv"
    lc.write_rows(target, [["a"]])
    with pytest.raises(lc.FileExistsRefused):
        lc.write_rows(target, [["b"]])
    assert "b" not in target.read_text(encoding="utf-8")
    lc.write_rows(target, [["b"]], force=True)
    assert '"b"' in target.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [target]


def test_stats_over_multiple_points_and_missing_label() -> None:
    series = {"group-labels": ["fcId=A"], "points": [[1, 1], [2, 3]]}
    row = lc.series_to_row(series, ["fcId", "deviceId"])
    assert row == ["A", "", "1", "3", "2", "4", ""]


def test_unknown_label_and_bad_columns_raise() -> None:
    with pytest.raises(ValueError):
        lc.series_to_row(_series(other="1"), ["fcId"])
    with pytest.raises(ValueError):
        lc.build_rows([], ["fcId"])


def test_part_file_name() -> None:
    assert lc.part_file_name("2026-10-08", "ctap") == "2026-10-08_ctap.csv"
    assert lc.part_file_name("2026-10-08", "ctap", 2) == "2026-10-08_02_ctap.csv"
    with pytest.raises(ValueError):
        lc.part_file_name("2026-10-08", "ctap", 0)
