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
        (tmp_path / "data" / "lightstep" / t).mkdir(parents=True, exist_ok=True)
        for kind in mod.KINDS:
            (tmp_path / "data" / "lightstep" / t / mod.output_file_name(kind, "2026-10-29")).write_text("x")


def test_steps_run_in_order_with_date_argument(tmp_path):
    _touch_reports(tmp_path)
    calls = []
    results = mod.run_steps(_steps(tmp_path), lambda argv, cwd, env: (calls.append(list(argv)) or (0, "")), cwd=tmp_path, env={})
    assert all(r.ok for r in results)
    names = [Path(c[1]).name for c in calls]
    assert names == ["export_lightstep_day.py"] * 2 + ["check_lightstep_inputs.py"] + ["run_pipeline.py", "extract_error_report_1xxx.py", "rank_households_by_error.py"] * 2
    assert calls[0][-2:] == ["--date", "2026-10-29"] and calls[2][3] == "29102026"
    assert calls[3][calls[3].index("--tenant") + 1] == "ZA" and "--skip-input-check" in calls[3]
    assert calls[-1][3].endswith("GH/2026-10-29_error_report_1xxx.csv")


def test_table_suffix_and_force_reach_only_run_pipeline_step(tmp_path):
    plain = {s.name: s.argv for s in _steps(tmp_path)}
    steps = mod.build_steps(DAY, ["ZA"], skip_export=False, top=10, python="py", investigation_dir=tmp_path, table_suffix="oct26", force=True)
    flagged = [s.name for s in steps if "--table-suffix" in s.argv]

    assert flagged == ["run_pipeline ZA"]
    assert next(s for s in steps if s.name == "run_pipeline ZA").argv[-3:] == ("--table-suffix", "oct26", "--force")
    assert "--table-suffix" not in plain["run_pipeline ZA"] and "--force" not in plain["run_pipeline ZA"]


def test_workers_is_passed_to_export_steps_only_when_given(tmp_path):
    with_workers = mod.build_steps(DAY, ["ZA"], skip_export=False, top=10, workers=6, python="py", investigation_dir=tmp_path)
    assert with_workers[0].argv[-2:] == ("--workers", "6")
    assert "--workers" not in _steps(tmp_path)[0].argv


def test_from_step_starts_at_the_named_group(tmp_path):
    names = lambda group: [s.name for s in mod.select_from_step(_steps(tmp_path), group)]  # noqa: E731  (one-line helper)
    assert names("pipeline")[0] == "run_pipeline ZA" and len(names("pipeline")) == 6
    assert names("rank") == ["rank households ZA", "run_pipeline GH", "error report 1xxx GH", "rank households GH"]
    assert len(names(None)) == len(_steps(tmp_path))
    with pytest.raises(ValueError):
        mod.select_from_step(_steps(tmp_path, skip_export=True), "export")


def test_skip_export_drops_export_steps(tmp_path):
    assert not any(s.name.startswith("export") for s in _steps(tmp_path, skip_export=True))


def test_failed_step_stops_pipeline_and_exits_nonzero(tmp_path):
    calls = []

    def runner(argv, cwd, env):
        calls.append(Path(argv[1]).name)
        return (1, "boom") if "run_pipeline.py" in argv[1] else (0, "")

    results = mod.run_steps(_steps(tmp_path, skip_export=True), runner, cwd=tmp_path, env={})
    assert calls == ["check_lightstep_inputs.py", "run_pipeline.py", "run_pipeline.py"]  # both tenants tried, none of their later steps
    assert [r.name for r in results if not r.ok] == ["run_pipeline ZA", "run_pipeline GH"]


def test_ranking_continues_across_tenants_after_one_failure(tmp_path):
    _touch_reports(tmp_path)
    runner = lambda argv, cwd, env: (1, "bad") if "/ZA/" in argv[3] else (0, "")  # noqa: E731  (one-line fake)
    results = mod.run_steps(_steps(tmp_path, skip_export=True), runner, cwd=tmp_path, env={})
    assert {r.name: r.ok for r in results if r.name.startswith("rank")} == {"rank households ZA": False, "rank households GH": True}


def test_missing_output_csv_fails_step(tmp_path):
    results = mod.run_steps(_steps(tmp_path, skip_export=True), lambda *a: (0, ""), cwd=tmp_path, env={})
    assert [r.name for r in results if not r.ok] == ["error report 1xxx ZA", "error report 1xxx GH"]


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


def test_failed_export_with_all_files_written_continues_but_exits_nonzero(tmp_path):
    steps = _steps(tmp_path)
    _touch_reports(tmp_path)
    runner = lambda argv, cwd, env: (1, "input check failed") if "export_lightstep_day.py" in argv[1] and "ZA" in argv else (0, "")  # noqa: E731
    results = mod.run_steps(steps, runner, cwd=tmp_path, env={})
    assert len(results) == len(steps) and [r.ok for r in results].count(False) == 1


def test_failed_export_without_files_blocks_only_that_tenant(tmp_path):
    _touch_reports(tmp_path)
    za_csv = tmp_path / "data" / "lightstep" / "ZA" / mod.output_file_name("ctap", "2026-10-29")
    za_csv.unlink()
    calls = []

    def runner(argv, cwd, env):
        calls.append(" ".join(Path(a).name for a in argv[1:]))
        return (1, "auth error") if "export_lightstep_day.py --tenant ZA" in calls[-1] else (0, "")

    steps = _steps(tmp_path)
    results = mod.run_steps(steps, runner, cwd=tmp_path, env={})

    assert [r.name for r in results if not r.ok] == ["export ZA"]
    assert not any("--tenant ZA" in c and "run_pipeline" in c for c in calls)
    assert any("run_pipeline.py" in c and "--tenant GH" in c for c in calls) and sum("rank_households_by_error.py" in c for c in calls) == 1
    text = "\n".join(t for _, t in mod.format_summary(steps, results, [], DAY, tenants=["ZA", "GH"]))
    assert "run_pipeline ZA: NOT RUN" in text and "run_pipeline GH: OK" in text
    assert "to resume: python3 run_daily_pipeline.py --date 29102026 --from-step export --tenants ZA" in text


def test_export_with_empty_kind_warning_is_ok_with_warning_and_exit_zero(tmp_path):
    _touch_reports(tmp_path)
    runner = lambda argv, cwd, env: (0, "OK       ctap: 3 rows\nWARNING  mdrm-cdm-playready: no series returned for 2026-10-29") if "--tenant" in argv and argv[argv.index("--tenant") + 1] == "ZA" and "export_lightstep_day.py" in argv[1] else (0, "")  # noqa: E731
    steps = _steps(tmp_path)
    results = mod.run_steps(steps, runner, cwd=tmp_path, env={})

    assert all(r.ok for r in results) and [r.name for r in results if r.warning] == ["export ZA"]
    text = "\n".join(t for _, t in mod.format_summary(steps, results, [], DAY, tenants=["ZA", "GH"]))
    assert "export ZA: OK with warning" in text and "nothing to resume" in text


def test_skip_input_check_drops_the_check_step(tmp_path):
    steps = mod.build_steps(DAY, ["ZA"], skip_export=True, top=10, python="py", investigation_dir=tmp_path, skip_input_check=True)
    assert [s.name for s in steps][0] == "run_pipeline ZA" and "check inputs" not in [s.name for s in steps]


def _coverage_inputs(tmp_path: Path, tenant: str, iso: str) -> None:
    (tmp_path / "data" / "athena" / tenant).mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "athena" / tenant / f"{iso}_session.csv").write_text("x")
    (tmp_path / "data" / "lightstep" / tenant).mkdir(parents=True, exist_ok=True)
    for kind in ("smvod", "smvod-release"):
        (tmp_path / "data" / "lightstep" / tenant / mod.output_file_name(kind, iso)).write_text("x")


def test_coverage_plan_uses_lagged_day_and_skips_tenants_with_missing_inputs(tmp_path):
    _coverage_inputs(tmp_path, "ZA", "2026-10-28")
    steps, skipped = mod.coverage_plan(DAY, ["ZA", "GH"], 1, python="py", investigation_dir=tmp_path)
    assert [s.name for s in steps] == ["ebvs release coverage ZA"]
    assert steps[0].argv[-4:] == ("--date", "2026-10-28", "--tenant", "ZA") and steps[0].continue_on_failure
    assert len(skipped) == 2 and "GH" in skipped[1] and "2026-10-28_session.csv" in skipped[1]
    assert "ebvs release coverage webview ZA" in skipped[0] and "2026-10-28_setupsession_with_outcome.csv" in skipped[0]


def test_coverage_plan_adds_webview_step_after_coverage_when_setupsession_report_exists(tmp_path):
    _coverage_inputs(tmp_path, "ZA", "2026-10-28")
    (tmp_path / "output" / "ZA").mkdir(parents=True)
    (tmp_path / "output" / "ZA" / "2026-10-28_setupsession_with_outcome.csv").write_text("x")
    steps, skipped = mod.coverage_plan(DAY, ["ZA"], 1, python="py", investigation_dir=tmp_path)
    assert [s.name for s in steps] == ["ebvs release coverage ZA", "ebvs release coverage webview ZA"] and not skipped
    assert steps[1].argv[1].endswith("analyze_release_gap_webview.py") and steps[1].continue_on_failure


def test_summary_reports_each_step_and_resume_command(tmp_path):
    _touch_reports(tmp_path)
    steps = _steps(tmp_path)
    results = [mod.StepResult(s.name, s.name != "run_pipeline ZA", 1.0) for s in steps[:4]]
    text = "\n".join(t for _, t in mod.format_summary(steps, results, ["ebvs release coverage GH (x): missing y"], DAY, tenants=["ZA", "GH"]))
    assert "run_pipeline ZA: FAILED" in text and "error report 1xxx ZA: NOT RUN" in text
    assert "rank households ZA: NOT RUN" in text
    assert "--date 29102026 --from-step pipeline" in text and "SKIPPED ebvs release coverage GH" in text


def test_summary_all_ok_needs_no_resume(tmp_path):
    steps = _steps(tmp_path)
    results = [mod.StepResult(s.name, True, 0.5) for s in steps]
    text = "\n".join(t for _, t in mod.format_summary(steps, results, [], DAY))
    assert "nothing to resume" in text and "to resume:" not in text
