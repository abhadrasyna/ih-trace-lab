"""Tests for Athena-derived CTAP/SM-VOD merge inputs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_SPEC = importlib.util.spec_from_file_location("ctap_smvod_merge_session_outcome", _SCRIPTS_DIR / "merge_session_outcome.py")
assert _SPEC and _SPEC.loader
merge_session_outcome = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(merge_session_outcome)


def test_find_input_file_prefers_iso_prefixed_athena_exports(tmp_path: Path) -> None:
    matching = tmp_path / "2026-09-30_session.csv"
    matching.write_text("sessionId\nabc\n", encoding="utf-8")

    found = merge_session_outcome.find_input_file(str(tmp_path), "session", "30092026")

    assert found == [str(matching)]


def test_merge_warns_when_no_athena_inputs_exist(tmp_path: Path, monkeypatch, capsys) -> None:
    report_path = tmp_path / "setupsession_30092026.csv"
    out_path = tmp_path / "setupsession_with_outcome_30092026.csv"
    report_path.write_text("sessionId\nabc\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_session_outcome.py",
            "--date",
            "30092026",
            "--input-dir",
            str(tmp_path / "data" / "athena"),
            "--report",
            str(report_path),
            "--out",
            str(out_path),
        ],
    )
    init_logging = Mock()
    monkeypatch.setattr(merge_session_outcome, "init_logging", init_logging)
    written: dict[str, object] = {}

    class FakeWriter:
        def __init__(self, handle, fieldnames, extrasaction="raise") -> None:
            written["path"] = handle.name
            written["fieldnames"] = fieldnames
            written["rows"] = []

        def writeheader(self) -> None:
            written["header"] = True

        def writerows(self, rows) -> None:
            written["rows"] = list(rows)

    monkeypatch.setattr(merge_session_outcome.csv, "DictWriter", FakeWriter)

    merge_session_outcome.main()

    stderr = capsys.readouterr().err
    init_logging.assert_called_once_with("ctap-smvod-merge_session_outcome")
    assert "WARNING: no Athena session enrichment file was found" in stderr
    assert "WARNING: no Athena debug enrichment files were found" in stderr
    assert written["path"] == str(out_path)


def test_merge_uses_legacy_debug_errors_without_debug_warning(tmp_path: Path, monkeypatch, capsys) -> None:
    report_path = tmp_path / "setupsession_30092026.csv"
    out_path = tmp_path / "setupsession_with_outcome_30092026.csv"
    input_dir = tmp_path / "data" / "athena"
    input_dir.mkdir(parents=True)
    report_path.write_text("sessionId\nabc\n", encoding="utf-8")
    (input_dir / "2026-09-30_debug_errors.csv").write_text(
        "eventid,eventdata,datetime\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_session_outcome.py",
            "--date",
            "30092026",
            "--input-dir",
            str(input_dir),
            "--report",
            str(report_path),
            "--out",
            str(out_path),
        ],
    )

    class FakeWriter:
        def __init__(self, handle, fieldnames, extrasaction="raise") -> None:
            self.handle = handle

        def writeheader(self) -> None:
            return None

        def writerows(self, rows) -> None:
            return None

    monkeypatch.setattr(merge_session_outcome.csv, "DictWriter", FakeWriter)

    merge_session_outcome.main()

    stderr = capsys.readouterr().err
    assert "WARNING: no Athena session enrichment file was found" in stderr
    assert "WARNING: no Athena debug enrichment files were found" not in stderr
