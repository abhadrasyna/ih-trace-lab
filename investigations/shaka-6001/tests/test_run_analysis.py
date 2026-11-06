"""Offline tests for the analysis runner: fake step runner, fake credential check, tmp_path data only (no AWS, no scripts run)."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts import run_analysis as ra
from src.lib.paths import YamlPathResolver

START, END = date(2026, 11, 4), date(2026, 11, 5)
RESOLVER = YamlPathResolver.from_file(ra.REPO_ROOT / "config" / "data_paths.yaml", ra.REPO_ROOT)


def make_env(tmp_path: Path, *, with_data: bool) -> ra.RunEnv:
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir(), out.mkdir()
    if with_data:
        for need in (*ra.REGISTRY["fetch_guest_login_redirects"].fetches, *ra.REGISTRY["build_6001_cohort"].fetches):
            for n in range((END - START).days + 1):
                (data / f"{START + timedelta(days=n)}_{need.artifact}.csv").write_text("a\n1\n")
    return ra.RunEnv(resolver=RESOLVER, sources=(data,), out_dir=out)


class FakeRunner:
    """Records the script of each call and writes the declared outputs, so no real script ever runs."""

    def __init__(self, env: ra.RunEnv, fail: tuple[str, ...] = ()):
        self.env, self.fail, self.calls = env, fail, []

    def __call__(self, argv, cwd, environ):
        script = Path(argv[1]).name
        step = next(s for s in ra.REGISTRY.values() if s.script == script)
        self.calls.append((step.name, list(argv)))
        if step.name in self.fail:
            return 1, "boom"
        start, end = date.fromisoformat(argv[argv.index("--start-date") + 1]), date.fromisoformat(argv[argv.index("--end-date") + 1])
        for path in ra.range_outputs(step, self.env, start, end):
            path.write_text("a\n1\n")
        return 0, "ok"

    @property
    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


def no_creds(tenant: str) -> None:
    raise AssertionError("credentials must not be checked when nothing is fetched")


def args(*extra: str) -> list[str]:
    return ["--start-date", START.isoformat(), "--end-date", END.isoformat(), *extra]


def test_runner_stops_on_missing_dates_without_flag(tmp_path, capsys):
    env = make_env(tmp_path, with_data=False)
    runner = FakeRunner(env)
    assert ra.main(args(), runner=runner, credential_check=no_creds, env=env) == ra.EXIT_USAGE
    assert runner.calls == []
    assert "--fetch-missing" in capsys.readouterr().err


def test_only_selects_steps(tmp_path):
    assert [s.name for s in ra.select_steps(["chart_before_after", "analyze_before_after"], ra.REGISTRY)] == [
        "analyze_before_after", "chart_before_after"]
    with pytest.raises(ra.RunnerError):
        ra.select_steps(["nope"], ra.REGISTRY)
    env = make_env(tmp_path, with_data=True)
    runner = FakeRunner(env)
    assert ra.main(args("--only", "analyze_before_after,rank_daily_top_models"), runner=runner, credential_check=no_creds,
                   env=env) == ra.EXIT_OK
    assert runner.names == ["analyze_before_after", "rank_daily_top_models"]


def test_steps_run_in_dependency_order(tmp_path):
    env = make_env(tmp_path, with_data=True)
    runner = FakeRunner(env)
    assert ra.main(args(), runner=runner, credential_check=no_creds, env=env) == ra.EXIT_OK
    position = {name: i for i, name in enumerate(runner.names)}
    assert set(position) == set(ra.REGISTRY)
    for step in ra.REGISTRY.values():
        assert all(position[d] < position[step.name] for d in (*step.depends_on, *step.after))
    custom: dict[str, ra.Step] = {}
    ra.register(ra.Step("late", "x.py", depends_on=("early",)), custom)
    ra.register(ra.Step("early", "y.py"), custom)
    assert [s.name for s in ra.select_steps(None, custom)] == ["early", "late"]


def test_failed_step_blocks_only_its_dependents(tmp_path):
    env = make_env(tmp_path, with_data=True)
    runner = FakeRunner(env, fail=("analyze_before_after",))
    assert ra.main(args(), runner=runner, credential_check=no_creds, env=env) == ra.EXIT_FAILED
    assert "chart_before_after" not in runner.names and "rank_daily_top_models" in runner.names


def test_credential_failure_marks_athena_steps_not_run_but_runs_local_steps(tmp_path):
    env = make_env(tmp_path, with_data=False)
    runner = FakeRunner(env)

    def expired(tenant: str) -> None:
        raise ra.CredentialError("expired")

    assert ra.main(args("--fetch-missing"), runner=runner, credential_check=expired, env=env) == ra.EXIT_FAILED
    assert "fetch_guest_login_redirects" not in runner.names and "build_6001_cohort" not in runner.names
    assert "analyze_6001_recovery" not in runner.names and "analyze_before_after" in runner.names


def test_cost_guard_skips_expensive_fetch(tmp_path):
    env = make_env(tmp_path, with_data=False)
    runner = FakeRunner(env)
    code = ra.main(args("--fetch-missing", "--max-scan-gb", "0.5"), runner=runner, credential_check=no_creds, env=env)
    assert code == ra.EXIT_FAILED and "fetch_guest_login_redirects" not in runner.names
