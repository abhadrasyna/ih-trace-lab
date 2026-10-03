"""Tests for PT-7 output path helpers used by CTAP/SM-VOD scripts."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_SPEC = importlib.util.spec_from_file_location("ctap_smvod_runtime", _SCRIPTS_DIR / "lib" / "runtime.py")
assert _SPEC and _SPEC.loader
runtime = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = runtime
_SPEC.loader.exec_module(runtime)

def test_snapshot_output_is_iso_prefixed(tmp_path: Path) -> None:
    output_path = runtime.snapshot_output_path("30092026", "setupsession_with_outcome", output_dir=tmp_path)

    assert output_path == str(tmp_path / "2026-09-30_setupsession_with_outcome.csv")


def test_rollup_output_has_marker(tmp_path: Path) -> None:
    output_path = runtime.rollup_output_path("mtn_escalation_all_dates", output_dir=tmp_path)

    assert output_path == str(tmp_path / "mtn_escalation_all_dates_rollup.csv")
