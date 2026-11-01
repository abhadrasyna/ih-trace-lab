from pathlib import Path

import pytest

from scripts.lib.lightstep_compare import compare_kind, find_files, read_rows


def _write(path: Path, text: str, bom: bool = False) -> None:
    path.write_text(text, encoding="utf-8-sig" if bom else "utf-8")


def test_compare_kind_counts_overlap_and_ignores_apostrophe(tmp_path: Path) -> None:
    _write(tmp_path / "m.csv", "a,sum\n'-1,5\n2,6\n3,7\n")
    _write(tmp_path / "g.csv", '"a","sum"\n"-1","5"\n"2","9"\n"4","1"\n', bom=True)
    result = compare_kind("ctap", read_rows([tmp_path / "m.csv"]), read_rows([tmp_path / "g.csv"]))
    assert (result.both, result.only_manual, result.only_generated, result.sum_different) == (2, 1, 1, 1)


def test_compare_kind_smvod_ts_keys_on_session_id_only(tmp_path: Path) -> None:
    _write(tmp_path / "m.csv", "sessionId,x\ns1,1\n")
    _write(tmp_path / "g.csv", "sessionId,y\ns1,2\ns2,3\n")
    result = compare_kind("smvod-ts", read_rows([tmp_path / "m.csv"]), read_rows([tmp_path / "g.csv"]))
    assert (result.both, result.only_generated, result.extra_columns) == (1, 1, ("y",))


def test_find_files_prefers_combined_then_parts_and_empty_when_missing(tmp_path: Path) -> None:
    assert find_files(tmp_path, "2026-10-29", "ctap") == []
    _write(tmp_path / "2026-10-29_01_ctap.csv", "a\n")
    assert len(find_files(tmp_path, "2026-10-29", "ctap")) == 1
    _write(tmp_path / "2026-10-29_ctap.csv", "a\n")
    assert find_files(tmp_path, "2026-10-29", "ctap") == [tmp_path / "2026-10-29_ctap.csv"]


def test_read_rows_rejects_mismatched_headers_and_ragged_rows(tmp_path: Path) -> None:
    _write(tmp_path / "a.csv", "a,sum\n1,2\n")
    _write(tmp_path / "b.csv", "a,other\n1,2\n")
    _write(tmp_path / "c.csv", "a,sum\n1,2,3\n")
    with pytest.raises(ValueError, match="differs"):
        read_rows([tmp_path / "a.csv", tmp_path / "b.csv"])
    with pytest.raises(ValueError, match="ragged"):
        read_rows([tmp_path / "c.csv"])


def test_compare_kind_raises_on_duplicate_keys() -> None:
    rows = [{"a": "1", "sum": "1"}, {"a": "1", "sum": "2"}]
    with pytest.raises(ValueError, match="duplicate key"):
        compare_kind("ctap", (["a", "sum"], rows), (["a", "sum"], rows))


def test_compare_kind_numeric_sums_and_required_sum_column() -> None:
    m = (["a", "sum"], [{"a": "1", "sum": "5.0"}])
    g = (["a", "sum"], [{"a": "1", "sum": "5"}])
    assert compare_kind("ctap", m, g).sum_different == 0
    with pytest.raises(ValueError, match="'sum' column"):
        compare_kind("ctap", (["a"], []), g)


def test_compare_kind_raises_without_shared_keys() -> None:
    with pytest.raises(ValueError, match="no shared key"):
        compare_kind("ctap", (["a", "sum"], []), (["b", "sum"], []))


def test_read_rows_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_rows([tmp_path / "nope.csv"])
