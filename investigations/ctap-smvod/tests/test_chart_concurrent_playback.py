"""Tests for chart_concurrent_playback.py (offline; renders to bytes only)."""
from __future__ import annotations

import pytest

from conftest import load_script
from src.lib.charts.errors import ChartError

mod = load_script("chart_concurrent_playback.py")


def summary() -> dict[str, dict[str, str]]:
    row = lambda v, p: {"view": v, "sessions_used": "10", "estimated_ends": "3", "peak": p, "peak_minute_utc": "12:46"}  # noqa: E731
    return {"csv_only": row("csv_only", "4"), "athena_exact": row("athena_exact", "5"), "athena_estimated": row("athena_estimated", "6")}


def series() -> dict[str, list[int]]:
    return {v: [i % 7 for i in range(1440)] for v in mod.VIEW_LABELS}


def test_header_cells_lead_with_estimated_peak():
    cells = mod.header_cells(summary())
    assert cells[0].value == "6 @ 12:46" and len(cells) == 5


def test_render_chart_returns_png():
    assert mod.render_chart(series(), summary(), "t")[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_chart_bad_input_raises_chart_error():
    with pytest.raises(ChartError):
        mod.render_chart({}, summary(), "t")


def test_chart_failure_does_not_block_report(tmp_path, monkeypatch):
    from datetime import date

    out = tmp_path / "ZA"
    out.mkdir()
    lines = ["minute_utc,csv_only,athena_exact,athena_estimated"] + [f"m{i},1,1,1" for i in range(1440)]
    (out / "2026-10-14_concurrent_playback.csv").write_text("\n".join(lines) + "\n")
    (out / "2026-10-14_concurrent_playback_summary.csv").write_text(
        "view,sessions_used,sessions_without_end,estimated_ends,unresolved,peak,peak_minute_utc\n"
        "csv_only,1,0,0,0,1,00:00\nathena_exact,1,0,0,0,1,00:00\nathena_estimated,1,0,0,0,1,00:00\n"
    )
    monkeypatch.setattr(mod, "render_chart", lambda *a, **k: (_ for _ in ()).throw(ChartError("boom")))
    assert mod.write_chart("ZA", date(2026, 10, 14), tmp_path) is False
    assert (out / "2026-10-14_concurrent_playback.csv").exists() and not (out / "2026-10-14_concurrent_playback.png").exists()
    monkeypatch.undo()
    assert mod.write_chart("ZA", date(2026, 10, 14), tmp_path) is True


def test_read_series_wrong_length_raises(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("minute_utc,csv_only,athena_exact,athena_estimated\n00:00,1,1,1\n")
    with pytest.raises(ValueError):
        mod.read_series(p)
    with pytest.raises(FileNotFoundError):
        mod.read_summary(tmp_path / "missing.csv")
