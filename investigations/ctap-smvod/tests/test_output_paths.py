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


def test_paths_are_tenant_scoped() -> None:
    root = runtime.repo_root() / "investigations" / "ctap-smvod"

    assert runtime.snapshot_output_path("30092026", "setupsession", tenant="ZM") == str(root / "output" / "ZM" / "2026-09-30_setupsession.csv")
    assert runtime.range_output_path("29092026", "30092026", "err", tenant="ZA") == str(root / "output" / "ZA" / "2026-09-29_2026-09-30_err.csv")
    assert runtime.rollup_output_path("x", tenant="ZM") == str(root / "output" / "ZM" / "x_rollup.csv")
    assert runtime.investigation_data_dir("lightstep", tenant="ZM") == root / "data" / "lightstep" / "ZM"
    assert runtime.investigation_data_dir("athena", tenant="ZA") == root / "data" / "athena" / "ZA"


def test_missing_tenant_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        runtime.snapshot_output_path("30092026", "setupsession", tenant="")
    with pytest.raises(ValueError):
        runtime.investigation_data_dir("lightstep", tenant="../ZM")
