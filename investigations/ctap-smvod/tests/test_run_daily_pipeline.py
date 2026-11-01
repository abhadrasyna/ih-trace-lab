"""Tests for run_daily_pipeline.py (fake step runner; nothing is executed)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from conftest import load_script

mod = load_script("run_daily_pipeline.py")
DAY = date(2026, 10, 29)


def _steps(tmp_path: Path, **kw):
    return mod.build_steps(DAY, ["ZA", "GH"], skip_export=kw.get("skip_export", False), top=10, python="py", investigation_dir=tmp_path)


def _touch_reports(tmp_path: Path) -> None:
    for t in ("ZA", "GH"):
        (tmp_path / "output" / t).mkdir(parents=True, exist_ok=True)
        (tmp_path / "output" / t / "2026-10-29_error_report_1xxx.csv").write_text("x")


def test_steps_run_in_order_with_date_argument(tmp_path):
    _touch_reports(tmp_path)
    calls = []
    results = mod.run_steps(_steps(tmp_path), lambda argv, cwd, env: (calls.append(list(argv)) or (0, "")), cwd=tmp_path, env={})
    assert all(r.ok for r in results)
    names = [Path(c[1]).name for c in calls]
    assert names == ["export_lightstep_day.py"] * 2 + ["check_lightstep_inputs.py", "run_pipeline.py", "extract_error_report_1xxx.py"] + ["rank_households_by_error.py"] * 2
    assert calls[0][-2:] == ["--date", "2026-10-29"] and calls[2][3] == "29102026"
    assert calls[-1][3].endswith("GH/2026-10-29_error_report_1xxx.csv")


def test_workers_is_passed_to_export_steps_only_when_given(tmp_path):
    with_workers = mod.build_steps(DAY, ["ZA"], skip_export=False, top=10, workers=6, python="py", investigation_dir=tmp_path)
    assert with_workers[0].argv[-2:] == ("--workers", "6")
    assert "--workers" not in _steps(tmp_path)[0].argv


def test_skip_export_drops_export_steps(tmp_path):
    assert not any(s.name.startswith("export") for s in _steps(tmp_path, skip_export=True))


def test_failed_step_stops_pipeline_and_exits_nonzero(tmp_path):
    calls = []

    def runner(argv, cwd, env):
        calls.append(Path(argv[1]).name)
        return (1, "boom") if "run_pipeline.py" in argv[1] else (0, "")

    results = mod.run_steps(_steps(tmp_path, skip_export=True), runner, cwd=tmp_path, env={})
    assert calls == ["check_lightstep_inputs.py", "run_pipeline.py"]
    assert [r.ok for r in results] == [True, False]


def test_ranking_continues_across_tenants_after_one_failure(tmp_path):
    _touch_reports(tmp_path)
    runner = lambda argv, cwd, env: (1, "bad") if "/ZA/" in argv[3] else (0, "")  # noqa: E731  (one-line fake)
    results = mod.run_steps(_steps(tmp_path, skip_export=True), runner, cwd=tmp_path, env={})
    assert [r.ok for r in results[-2:]] == [False, True]


def test_missing_output_csv_fails_step(tmp_path):
    results = mod.run_steps(_steps(tmp_path, skip_export=True), lambda *a: (0, ""), cwd=tmp_path, env={})
    assert results[-1].name == "error report 1xxx" and not results[-1].ok


def test_parse_day_formats_and_default():
    assert mod.parse_day("29102026") == mod.parse_day("2026-10-29") == DAY
    assert mod.default_day(datetime(2026, 11, 2, 7, 30, tzinfo=timezone.utc)) == date(2026, 11, 1)
    with pytest.raises(ValueError):
        mod.parse_day("2026/10/29")


def test_main_runs_with_fake_runner_and_writes_dated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "INVESTIGATION_DIR", tmp_path)
    calls = []
    code = mod.main(["--date", "29102026", "--skip-export", "--tenants", "ZA", "--log-dir", str(tmp_path / "logs")],
                    runner=lambda argv, cwd, env: (calls.append(env["FCID"]) or (0, "")))
    assert code == 1 and len(calls) == 3  # report CSV missing -> extract step fails, ranking not run
    assert (tmp_path / "logs" / "run-daily-pipeline_2026-10-29.log").is_file()


def test_runner_times_out_hung_step():
    code, out = mod.make_subprocess_runner(0.2)(["python3", "-c", "import time; time.sleep(5)"], Path("."), {})
    assert code == 124 and "timed out" in out
