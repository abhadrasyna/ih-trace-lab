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


class _Args:
    date = "30092026"
    tenant = None
    profile = None
    skip_auth_check = False
    skip_if_exists = False
    force = False
    skip_step3 = False
    skip_step4 = False
    skip_step6b = False
    skip_step6d = False
    skip_step6e = False
    skip_error_eventdata = False
    full_position_report = False
    dry_run = False


def _args(**overrides: object) -> _Args:
    args = _Args()
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


@pytest.fixture
def tenant_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def tenant_dirs(tenant: str) -> dict[str, str]:
        return {
            "lightstep": str(tmp_path / "data" / "lightstep" / tenant),
            "athena": str(tmp_path / "data" / "athena" / tenant),
            "output": str(tmp_path / "output" / tenant),
        }

    monkeypatch.setattr(run_pipeline, "_tenant_dirs", tenant_dirs)
    monkeypatch.setattr(run_pipeline, "init_logging", Mock())
    return tmp_path


def _write_inputs(root: Path, tenant: str, names=("2026-09-30_ctap.csv", "2026-09-30_smvod.csv")) -> Path:
    folder = root / "data" / "lightstep" / tenant
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text("header\n", encoding="utf-8")
    return folder


def test_step2_reads_iso_prefixed_lightstep_files(tenant_root: Path) -> None:
    folder = _write_inputs(tenant_root, "ZM", ("2026-09-30_ctap.csv", "2026-09-30_smvod.csv", "2026-09-30_smvod-ts.csv"))

    resolved = run_pipeline._ensure_step2_inputs_exist("30092026", "ZM")

    assert resolved == {
        "ctap": str(folder / "2026-09-30_ctap.csv"),
        "smvod": str(folder / "2026-09-30_smvod.csv"),
        "smvod-ts": str(folder / "2026-09-30_smvod-ts.csv"),
    }


def test_step2_missing_file_error_message_names_tenant_path(tenant_root: Path) -> None:
    _write_inputs(tenant_root, "ZM", ("2026-09-30_ctap.csv",))

    with pytest.raises(FileNotFoundError) as exc_info:
        run_pipeline._ensure_step2_inputs_exist("30092026", "ZM")

    message = str(exc_info.value)
    assert "data/lightstep/ZM" in message
    assert "2026-09-30_smvod.csv" in message
    assert "2026-09-30_smvod-ts.csv" in message


def test_step34_paths_are_tenant_scoped(tenant_root: Path) -> None:
    athena = tenant_root / "data" / "athena" / "ZM"
    assert run_pipeline._step3_output_path("30092026", "ZM") == str(athena / "2026-09-30_session.csv")
    assert run_pipeline._step4_output_path("30092026", "ZM") == str(athena / "2026-09-30_debug_states.csv")


def test_build_steps_passes_tenant_and_athena_output_dir(tenant_root: Path) -> None:
    steps = run_pipeline._build_steps(_args(profile="demo", skip_auth_check=True), "2026-09-30", "ZM")
    athena_dir = str(tenant_root / "data" / "athena" / "ZM")

    assert steps[0][0].startswith("Step 1b")
    for index in (2, 3):
        assert ["--tenant", "ZM", "--output-dir", athena_dir] == steps[index][1][-4:]


def test_build_steps_scopes_every_step_to_tenant_folders(tenant_root: Path) -> None:
    steps = run_pipeline._build_steps(_args(), "2026-09-30", "ZM")
    lightstep = str(tenant_root / "data" / "lightstep" / "ZM")
    out = tenant_root / "output" / "ZM"

    label, command, skip = steps[0]
    assert label.startswith("Step 1b") and skip is False
    assert command[1].endswith("combine_lightstep_parts.py")
    assert command[-4:] == ["--date", "2026-09-30", "--input-dir", lightstep]
    assert ["--input-dir", lightstep] == steps[1][1][-6:-4]
    assert ["--tenant", "ZM"] == steps[1][1][-2:]
    assert all(str(out) in " ".join(c) for _, c, _ in steps[1:2] + steps[4:8])


def test_build_steps_adds_error_eventdata_fetch_and_flatten(tenant_root: Path) -> None:
    steps = run_pipeline._build_steps(_args(skip_auth_check=True), "2026-09-30", "ZM")
    athena_dir = str(tenant_root / "data" / "athena" / "ZM")
    out = tenant_root / "output" / "ZM"

    fetch, flatten = steps[-2], steps[-1]
    assert fetch[0].startswith("Step 6f") and fetch[1][1].endswith("run_athena_error_eventdata.py")
    assert ["--tenant", "ZM", "--output-dir", athena_dir] == fetch[1][-4:]
    assert flatten[0].startswith("Step 6g") and flatten[1][1].endswith("flatten_error_eventdata.py")
    assert flatten[1][flatten[1].index("--input") + 1] == str(Path(athena_dir) / "2026-09-30_error_eventdata.csv")
    assert flatten[1][flatten[1].index("--out-dir") + 1] == str(out / "error_eventdata_flat")
    assert flatten[1][flatten[1].index("--date") + 1] == "2026-09-30"
    assert "--split-by-errorcode" in flatten[1] and fetch[2] is False and flatten[2] is False


def test_build_steps_skip_error_eventdata_skips_both(tenant_root: Path) -> None:
    steps = run_pipeline._build_steps(_args(skip_error_eventdata=True), "2026-09-30", "ZM")
    assert steps[-2][2] is True and steps[-1][2] is True


def test_build_steps_forwards_force_to_athena_steps(tenant_root: Path) -> None:
    steps = run_pipeline._build_steps(_args(force=True, skip_auth_check=True), "2026-09-30", "ZM")

    assert "--force" in steps[2][1]
    assert "--force" in steps[3][1]


def _run_main(monkeypatch: pytest.MonkeyPatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--date", "30092026", *argv])
    run_pipeline.main()


_SKIPS = ("--skip-step3", "--skip-step4", "--skip-step6b", "--skip-step6d", "--skip-step6e", "--skip-error-eventdata")


def test_main_validates_inputs_after_step1b_not_before(
    tenant_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A date that only has numbered parts must not be rejected before Step 1b produces the whole-day files.
    folder = _write_inputs(tenant_root, "ZM", ("2026-09-30_01_ctap.csv", "2026-09-30_01_smvod.csv"))
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: ["ZM"])

    def fake_subprocess_run(command, *args, **kwargs):
        if command[1].endswith("combine_lightstep_parts.py"):
            (folder / "2026-09-30_ctap.csv").write_text("header\n", encoding="utf-8")
            (folder / "2026-09-30_smvod.csv").write_text("header\n", encoding="utf-8")
        return Mock(returncode=0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_subprocess_run)

    _run_main(monkeypatch, *_SKIPS)

    assert "Pipeline complete for 30092026." in capsys.readouterr().err


def test_main_dry_run_calls_init_logging_and_prints_tenant(
    tenant_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: ["ZM"])

    _run_main(monkeypatch, "--dry-run")

    run_pipeline.init_logging.assert_called_once_with("ctap-smvod-run_pipeline")
    out = capsys.readouterr().out
    assert "# [ZM] Step 1b - combine split Lightstep CSV parts (combine_lightstep_parts.py)" in out
    assert "# [ZM] Step 2 - base merge (merge_ctap_smvod_csv.py)" in out


def _record_runs(monkeypatch: pytest.MonkeyPatch, failing_tenant: str | None = None) -> list[str]:
    ran: list[str] = []

    def fake_run(command, *args, **kwargs):
        tenant = command[command.index("--input-dir") + 1].split("/")[-1] if "--input-dir" in command else ""
        if command[1].endswith("combine_lightstep_parts.py"):
            ran.append(tenant)
            return Mock(returncode=3 if tenant == failing_tenant else 0)
        return Mock(returncode=0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)
    return ran


def test_default_runs_all_discovered_tenants(tenant_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_inputs(tenant_root, "SA")
    _write_inputs(tenant_root, "ZM")
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: ["SA", "ZM"])
    ran = _record_runs(monkeypatch)

    _run_main(monkeypatch, *_SKIPS)

    assert ran == ["SA", "ZM"]


def test_tenant_flag_runs_only_that_tenant(tenant_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_inputs(tenant_root, "ZM")
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: pytest.fail("must not discover"))
    monkeypatch.setattr(run_pipeline, "resolve_tenant_context", lambda code: Mock(code=code))
    monkeypatch.setattr(run_pipeline, "require_lightstep_dir", lambda code: None)
    ran = _record_runs(monkeypatch)

    _run_main(monkeypatch, "--tenant", "ZM", *_SKIPS)

    assert ran == ["ZM"]


def test_one_failure_does_not_stop_others_and_exits_nonzero(
    tenant_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_inputs(tenant_root, "SA")
    _write_inputs(tenant_root, "ZM")
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: ["SA", "ZM"])
    ran = _record_runs(monkeypatch, failing_tenant="SA")

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, *_SKIPS)

    assert exc_info.value.code != 0
    assert ran == ["SA", "ZM"]
    err = capsys.readouterr().err
    assert "SA: FAILED" in err and "ZM: OK" in err


def test_no_tenant_input_fails_loudly(
    tenant_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_pipeline, "discover_tenants", lambda date_iso: [])
    monkeypatch.setattr(run_pipeline, "investigation_data_dir", lambda tool, tenant=None: tenant_root / "data" / tool)

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, *_SKIPS)

    assert exc_info.value.code == 1
    assert "No tenant has Lightstep input for 2026-09-30" in capsys.readouterr().err
