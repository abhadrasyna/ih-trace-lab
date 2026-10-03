"""Tests for the migrated CTAP/SM-VOD pipeline path checks."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_SPEC = importlib.util.spec_from_file_location("ctap_smvod_run_pipeline", _SCRIPTS_DIR / "run_pipeline.py")
assert _SPEC and _SPEC.loader
run_pipeline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_pipeline)


def test_step2_reads_iso_prefixed_lightstep_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lightstep_dir = tmp_path / "data" / "lightstep"
    lightstep_dir.mkdir(parents=True)
    for name in ("2026-09-30_ctap.csv", "2026-09-30_smvod.csv", "2026-09-30_smvod-ts.csv"):
        (lightstep_dir / name).write_text("header\n", encoding="utf-8")

    monkeypatch.setattr(run_pipeline, "LIGHTSTEP_DIR", str(lightstep_dir))

    resolved = run_pipeline._ensure_step2_inputs_exist("30092026")

    assert resolved == {
        "ctap": str(lightstep_dir / "2026-09-30_ctap.csv"),
        "smvod": str(lightstep_dir / "2026-09-30_smvod.csv"),
        "smvod-ts": str(lightstep_dir / "2026-09-30_smvod-ts.csv"),
    }


def test_step2_missing_file_error_message_names_new_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lightstep_dir = tmp_path / "data" / "lightstep"
    lightstep_dir.mkdir(parents=True)
    (lightstep_dir / "2026-09-30_ctap.csv").write_text("header\n", encoding="utf-8")

    monkeypatch.setattr(run_pipeline, "LIGHTSTEP_DIR", str(lightstep_dir))

    with pytest.raises(FileNotFoundError) as exc_info:
        run_pipeline._ensure_step2_inputs_exist("30092026")

    message = str(exc_info.value)
    assert "data/lightstep" in message
    assert "inputCSV" not in message
    assert "2026-09-30_smvod.csv" in message
    assert "2026-09-30_smvod-ts.csv" in message
