"""Tests for Athena-pull pathing in the migrated CTAP/SM-VOD scripts."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


playback = _load_module("ctap_smvod_run_athena_playback", "run_athena_playback_outcome.py")
debug = _load_module("ctap_smvod_run_athena_debug", "run_athena_debug_events.py")


def _run_cli(module, argv: list[str], monkeypatch, fake_run_query, *, fake_extract_ids=None) -> dict[str, object]:
    captured: dict[str, object] = {}
    init_logging_calls: list[str] = []

    def recorder(**kwargs):
        captured.update(kwargs)
        return fake_run_query(**kwargs)

    monkeypatch.setattr(module, "init_logging", lambda slug: init_logging_calls.append(slug))
    monkeypatch.setattr(module, "run_athena_query", recorder)
    if fake_extract_ids is not None:
        monkeypatch.setattr(module.extract_session_ids, "extract_ids", fake_extract_ids)
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    captured["init_logging_calls"] = init_logging_calls
    return captured


@pytest.mark.parametrize(
    ("module", "argv", "expected_name", "extract_ids", "expected_slug"),
    [
        (
            playback,
            ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--output-dir"],
            "2026-09-30_session.csv",
            None,
            "ctap-smvod-run_athena_playback_outcome",
        ),
        (
            debug,
            ["run_athena_debug_events.py", "--date", "2026-09-30", "--input"],
            "2026-09-30_debug_states.csv",
            lambda path, column: ["abc"],
            "ctap-smvod-run_athena_debug_events",
        ),
    ],
)
def test_athena_pull_writes_iso_prefixed_file(
    tmp_path: Path, monkeypatch, module, argv, expected_name, extract_ids, expected_slug
) -> None:
    report_path = tmp_path / "setupsession_30092026.csv"
    report_path.write_text("sessionId\nabc\n", encoding="utf-8")
    cli = list(argv)
    if "--output-dir" in cli:
        cli.extend([str(tmp_path), "--skip-auth-check"])
    else:
        cli.extend([str(report_path), "--output-dir", str(tmp_path), "--skip-auth-check"])

    captured = _run_cli(
        module,
        cli,
        monkeypatch,
        lambda **kwargs: SimpleNamespace(row_count=1),
        fake_extract_ids=extract_ids,
    )

    assert captured["output_path"] == str(tmp_path / expected_name)
    assert captured["init_logging_calls"] == [expected_slug]


def test_athena_pull_uses_lib_adapter(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    captured = _run_cli(
        playback,
        ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--output-dir", str(tmp_path), "--skip-auth-check"],
        monkeypatch,
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(row_count=1),
    )

    assert len(calls) == 1
    assert captured["database"] == "unified_e6auj7k7"
    assert captured["profile"] == "clarissa-insights-product"


def test_athena_pull_rejects_non_iso_date(monkeypatch, capsys) -> None:
    monkeypatch.setattr(playback, "run_athena_query", lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")))
    monkeypatch.setattr(sys, "argv", ["run_athena_playback_outcome.py", "--date", "30092026", "--skip-auth-check"])

    with pytest.raises(SystemExit) as exc_info:
        playback.main()

    assert exc_info.value.code == 1
    assert "ERROR: --date must be YYYY-MM-DD" in capsys.readouterr().err


def test_athena_pull_skips_when_csv_already_has_data(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "2026-09-30_session.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    argv = ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--output-dir", str(tmp_path), "--skip-auth-check"]
    calls: list[dict[str, object]] = []

    _run_cli(playback, argv, monkeypatch, lambda **kwargs: calls.append(kwargs) or SimpleNamespace(row_count=1))
    assert calls == []

    _run_cli(playback, [*argv, "--force"], monkeypatch, lambda **kwargs: calls.append(kwargs) or SimpleNamespace(row_count=1))
    assert len(calls) == 1


def test_athena_pull_fires_when_existing_csv_is_header_only(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "2026-09-30_session.csv").write_text("a,b\n", encoding="utf-8")
    calls: list[dict[str, object]] = []

    _run_cli(
        playback,
        ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--output-dir", str(tmp_path), "--skip-auth-check"],
        monkeypatch,
        lambda **kwargs: calls.append(kwargs) or SimpleNamespace(row_count=1),
    )

    assert len(calls) == 1


def test_athena_pull_uses_tenant_registry_values(tmp_path: Path, monkeypatch) -> None:
    captured = _run_cli(
        playback,
        ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--tenant", "ZM", "--output-dir", str(tmp_path), "--skip-auth-check"],
        monkeypatch,
        lambda **kwargs: SimpleNamespace(row_count=1),
    )

    assert captured["database"] == "unified_a7vli5h8"
    assert 'unified_a7vli5h8' in captured["sql"]


def test_debug_events_query_uses_tenant_table(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "setupsession.csv"
    report_path.write_text("sessionId\nabc\n", encoding="utf-8")

    captured = _run_cli(
        debug,
        ["run_athena_debug_events.py", "--date", "2026-09-30", "--tenant", "ZM", "--input", str(report_path),
         "--output-dir", str(tmp_path), "--skip-auth-check"],
        monkeypatch,
        lambda **kwargs: SimpleNamespace(row_count=1),
        fake_extract_ids=lambda path, column: ["abc"],
    )

    assert 'FROM "unified_a7vli5h8"."a7vli5h8_ccl_debug_events"' in captured["sql"]
    assert "e6auj7k7" not in captured["sql"]


def test_athena_pull_unknown_tenant_exits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["run_athena_playback_outcome.py", "--date", "2026-09-30", "--tenant", "XX", "--skip-auth-check"])

    with pytest.raises(SystemExit) as exc_info:
        playback.main()

    assert exc_info.value.code == 1
    assert "Unknown tenant 'XX'" in capsys.readouterr().err
