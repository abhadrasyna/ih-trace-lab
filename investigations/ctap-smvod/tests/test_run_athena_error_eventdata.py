"""Tests for run_athena_error_eventdata.py (offline: no Athena, no AWS)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import load_script

mod = load_script("run_athena_error_eventdata.py")

CTX = SimpleNamespace(code="ZM", debug_events_table="a7vli5h8_ccl_debug_events", profile="p", database="unified_a7vli5h8",
                      region="eu-central-1")


def test_parse_codes_splits_and_strips():
    assert mod.parse_codes("3016, 6007,,E31012") == ["3016", "6007", "E31012"]
    assert mod.parse_codes(None) == []


def test_parse_codes_rejects_sql_injection_tokens():
    with pytest.raises(ValueError, match="invalid error code"):
        mod.parse_codes("3016') OR 1=1 --")


def test_build_query_without_codes_has_no_code_filter():
    sql = mod.build_query(CTX, "unified_a7vli5h8", "2026-10-04", [])
    assert "eventid = 'PLAYER_ERROR'" in sql and "a7vli5h8_ccl_debug_events" in sql
    assert "datetime >= '2026-10-04T00:00:00.000Z'" in sql and "datetime <  '2026-10-05T00:00:00.000Z'" in sql
    assert "$.errorcode" not in sql and "{{" not in sql


def test_build_query_with_codes_filters_on_errorcode():
    sql = mod.build_query(CTX, "unified_a7vli5h8", "2026-10-31", ["3016", "6007"])
    assert "json_extract_scalar(eventdata, '$.errorcode') IN ('3016', '6007')" in sql
    assert "datetime <  '2026-11-01T00:00:00.000Z'" in sql


def test_output_path_uses_date_and_dir():
    assert mod.output_path("2026-10-04", "d") == str(Path("d") / "2026-10-04_error_eventdata.csv")


def _run_main(monkeypatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["run_athena_error_eventdata.py", *argv])
    monkeypatch.setattr(mod, "init_logging", lambda slug: None)
    monkeypatch.setattr(mod, "resolve_tenant_context", lambda code: CTX)
    mod.main()


def test_main_dry_run_prints_query_and_skips_athena(monkeypatch, capsys):
    monkeypatch.setattr(mod, "run_athena_query", lambda **kw: pytest.fail("Athena must not run on --dry-run"))
    _run_main(monkeypatch, "--date", "2026-10-04", "--tenant", "ZM", "--codes", "3016", "--dry-run")
    assert "IN ('3016')" in capsys.readouterr().out


def test_main_rejects_bad_date(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--date", "04102026", "--tenant", "ZM", "--dry-run")
    assert exc.value.code == 1 and "ERROR" in capsys.readouterr().err


def test_main_runs_query_to_tenant_output(monkeypatch, tmp_path):
    seen = {}

    def fake_run(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(row_count=3)

    monkeypatch.setattr(mod, "run_athena_query", fake_run)
    _run_main(monkeypatch, "--date", "2026-10-04", "--tenant", "ZM", "--output-dir", str(tmp_path), "--skip-auth-check")
    assert seen["output_path"] == str(tmp_path / "2026-10-04_error_eventdata.csv")
    assert seen["database"] == "unified_a7vli5h8" and seen["profile"] == "p"


def test_output_path_embeds_sorted_codes():
    assert mod.output_path("2026-10-04", "d", ["6007", "3016"]) == str(Path("d") / "2026-10-04_error_eventdata_codes-3016-6007.csv")


def test_filtered_run_does_not_serve_unfiltered_run(monkeypatch, tmp_path):
    runs = []

    def fake_run(**kwargs):
        Path(kwargs["output_path"]).write_text("datetime\nx\n")
        runs.append(kwargs["output_path"])
        return SimpleNamespace(row_count=1)

    monkeypatch.setattr(mod, "run_athena_query", fake_run)
    base = ("--date", "2026-10-04", "--tenant", "ZM", "--output-dir", str(tmp_path), "--skip-auth-check")
    _run_main(monkeypatch, *base, "--codes", "3016")
    _run_main(monkeypatch, *base)
    assert len(runs) == 2 and runs[0] != runs[1]


def test_pipeline_athena_flags_are_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "run_athena_query", lambda **kw: SimpleNamespace(row_count=0))
    _run_main(monkeypatch, "--date", "2026-10-04", "--profile", "p", "--skip-auth-check", "--force",
              "--tenant", "ZM", "--output-dir", str(tmp_path))
