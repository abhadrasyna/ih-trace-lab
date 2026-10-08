"""Tests for summarize_pipeline_run.py."""
from __future__ import annotations

import sys

from conftest import load_script

mod = load_script("summarize_pipeline_run.py")


def test_error_token_counts_once_per_session():
    rows = [{"error_codes": "1003;E31012"}, {"error_codes": "1003, 1003"}, {"error_codes": ""}]
    assert mod.error_token_counts(rows) == {"1003": 2, "E31012": 1}


def test_render_reports_overlap_and_counts():
    exports = {"ctap": [{"lightstep.trace_id": "a"}], "smvod": [{"lightstep.trace_id": "a"}, {"lightstep.trace_id": "b"}],
               "smvod-ts": [{"sessionId": "s"}]}
    out = mod.render("ZM", "2026-10-01", exports, [{"error_codes": "1003"}, {"error_codes": ""}])
    assert "ctap ∩ smvod traces: 1; ctap only: 0; smvod only: 1" in out
    assert "| 1003 | 1 |" in out and "sessions with error codes: 1 of 2" in out


def test_missing_files_exit_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["x", "--date", "01102026", "--tenant", "ZM", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "ERROR" in capsys.readouterr().err


def test_missing_required_column_exits_nonzero(tmp_path, monkeypatch, capsys):
    for sub in ("data/lightstep/ZM", "output/ZM"):
        (tmp_path / sub).mkdir(parents=True)
    for n in mod.EXPORTS:
        (tmp_path / f"data/lightstep/ZM/2026-10-01_{n}.csv").write_text("lightstep.trace_id\nt1\n")
    (tmp_path / "output/ZM/2026-10-01_setupsession_with_outcome.csv").write_text("sessionId\ns1\n")
    monkeypatch.setattr(sys, "argv", ["x", "--date", "01102026", "--tenant", "ZM", "--root", str(tmp_path)])
    assert mod.main() == 1
    assert "error_codes" in capsys.readouterr().err
