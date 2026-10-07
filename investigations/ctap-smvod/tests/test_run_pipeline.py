"""Tests for the migrated CTAP/SM-VOD pipeline path checks."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

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


def test_step34_paths_use_data_athena_and_skip_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    athena_dir = tmp_path / "data" / "athena"
    athena_dir.mkdir(parents=True)
    monkeypatch.setattr(run_pipeline, "ATHENA_DIR", str(athena_dir))

    assert run_pipeline._step3_output_path("30092026") == str(athena_dir / "2026-09-30_session.csv")
    assert run_pipeline._step4_output_path("30092026") == str(athena_dir / "2026-09-30_debug_states.csv")


def test_build_steps_passes_athena_output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    athena_dir = tmp_path / "data" / "athena"
    athena_dir.mkdir(parents=True)
    monkeypatch.setattr(run_pipeline, "ATHENA_DIR", str(athena_dir))

    class Args:
        date = "30092026"
        profile = "demo"
        skip_auth_check = True
        skip_if_exists = False
        force = False
        skip_step3 = False
        skip_step4 = False
        skip_step6b = False
        skip_step6d = False
        skip_step6e = False
        full_position_report = False

    steps = run_pipeline._build_steps(Args(), "2026-09-30")

    assert steps[0][0].startswith("Step 1b")
    assert ["--output-dir", str(athena_dir)] == steps[2][1][-2:]
    assert ["--output-dir", str(athena_dir)] == steps[3][1][-2:]


def test_build_steps_step1b_combines_lightstep_parts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lightstep_dir = tmp_path / "data" / "lightstep"
    monkeypatch.setattr(run_pipeline, "LIGHTSTEP_DIR", str(lightstep_dir))

    class Args:
        date = "30092026"
        profile = None
        skip_auth_check = False
        skip_if_exists = False
        force = False
        skip_step3 = True
        skip_step4 = True
        skip_step6b = True
        skip_step6d = True
        skip_step6e = True
        full_position_report = False

    steps = run_pipeline._build_steps(Args(), "2026-09-30")

    label, command, skip = steps[0]
    assert label.startswith("Step 1b")
    assert skip is False
    assert command[1].endswith("combine_lightstep_parts.py")
    assert command[-4:] == ["--date", "2026-09-30", "--input-dir", str(lightstep_dir)]


def test_main_validates_inputs_after_step1b_not_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Edge case: a date that only has numbered parts (no whole-day _ctap.csv/
    # _smvod.csv yet) must not be rejected before Step 1b runs -- Step 1b is
    # what's expected to produce the whole-day files from the parts.
    lightstep_dir = tmp_path / "data" / "lightstep"
    lightstep_dir.mkdir(parents=True)
    (lightstep_dir / "2026-09-30_01_ctap.csv").write_text("header\n", encoding="utf-8")
    (lightstep_dir / "2026-09-30_01_smvod.csv").write_text("header\n", encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "LIGHTSTEP_DIR", str(lightstep_dir))
    monkeypatch.setattr(sys, "argv", [
        "run_pipeline.py", "--date", "30092026",
        "--skip-step3", "--skip-step4", "--skip-step6b", "--skip-step6d", "--skip-step6e",
    ])
    monkeypatch.setattr(run_pipeline, "init_logging", Mock())

    def fake_subprocess_run(command, *args, **kwargs):
        if command[1].endswith("combine_lightstep_parts.py"):
            # Simulate what combine_lightstep_parts.py actually does: produce
            # the whole-day files the numbered parts were split from.
            (lightstep_dir / "2026-09-30_ctap.csv").write_text("header\n", encoding="utf-8")
            (lightstep_dir / "2026-09-30_smvod.csv").write_text("header\n", encoding="utf-8")
        return Mock(returncode=0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_subprocess_run)

    run_pipeline.main()

    out = capsys.readouterr().err
    assert "Pipeline complete for 30092026." in out


def test_main_dry_run_calls_init_logging(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--date", "30092026", "--dry-run"])
    init_logging = Mock()
    monkeypatch.setattr(run_pipeline, "init_logging", init_logging)

    run_pipeline.main()

    init_logging.assert_called_once_with("ctap-smvod-run_pipeline")
    out = capsys.readouterr().out
    assert "# Step 1b - combine split Lightstep CSV parts (combine_lightstep_parts.py)" in out
    assert "# Step 2 - base merge (merge_ctap_smvod_csv.py)" in out


def test_build_steps_forwards_force_to_athena_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_pipeline, "ATHENA_DIR", str(tmp_path))

    class Args:
        date = "30092026"
        profile = None
        skip_auth_check = True
        skip_if_exists = False
        force = True
        skip_step3 = False
        skip_step4 = False
        skip_step6b = False
        skip_step6d = False
        skip_step6e = False
        full_position_report = False

    steps = run_pipeline._build_steps(Args(), "2026-09-30")

    assert "--force" in steps[2][1]
    assert "--force" in steps[3][1]
