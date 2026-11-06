"""Offline tests for the daily cron entry point: fake runner/credentials, tmp_path only (no AWS, no real scripts)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts import run_analysis as ra
from scripts import run_daily as rd
from src.lib.paths import YamlPathResolver

RESOLVER = YamlPathResolver.from_file(ra.REPO_ROOT / "config" / "data_paths.yaml", ra.REPO_ROOT)
NOW = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)  # last complete UTC day: 2026-11-05
TARGET, FIRST = date(2026, 11, 5), date(2026, 11, 1)


def make_env(tmp_path: Path, *, with_data: bool = True) -> ra.RunEnv:
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir(), out.mkdir()
    if with_data:
        for need in (*ra.REGISTRY["fetch_guest_login_redirects"].fetches, *ra.REGISTRY["build_6001_cohort"].fetches):
            for n in range((TARGET - FIRST).days + 1):
                (data / f"{FIRST + timedelta(days=n)}_{need.artifact}.csv").write_text("a\n1\n")
    return ra.RunEnv(resolver=RESOLVER, sources=(data,), out_dir=out)


class FakeRunner:
    def __init__(self, env: ra.RunEnv, fail: tuple[str, ...] = ()):
        self.env, self.fail, self.calls = env, fail, []

    def __call__(self, argv, cwd, environ):
        step = next(s for s in ra.REGISTRY.values() if s.script == Path(argv[1]).name)
        end = date.fromisoformat(argv[argv.index("--end-date") + 1])
        self.calls.append((step.name, end))
        if step.name in self.fail:
            return 1, "boom"
        for path in ra.range_outputs(step, self.env, FIRST, end):
            path.write_text("a\n1\n")
        return 0, "ok"


def never(tenant: str) -> None:
    raise AssertionError("credentials must not be checked when nothing is fetched")


def run(tmp_path, env, runner, check=never):
    return rd.main(["--log-dir", str(tmp_path / "logs")], runner=runner, credential_check=check, env=env, now=NOW)


def write_outputs(env: ra.RunEnv, end: date) -> None:
    for step in ra.REGISTRY.values():
        for path in ra.range_outputs(step, env, FIRST, end):
            path.write_text("a\n1\n")


def test_daily_backfills_missing_dates(tmp_path):
    env = make_env(tmp_path)
    for done in (date(2026, 11, 2), date(2026, 11, 4)):
        write_outputs(env, done)
    runner = FakeRunner(env)
    assert run(tmp_path, env, runner) == ra.EXIT_OK
    ends = sorted({end for _, end in runner.calls})
    assert ends == [date(2026, 11, 3), TARGET]
    assert not (env.out_dir / f"{TARGET}.FAILED.txt").exists()


def test_daily_second_instance_exits_on_lock(tmp_path):
    env = make_env(tmp_path)
    held = rd.acquire_lock(tmp_path / "logs" / rd.LOCK_NAME)
    assert held is not None
    try:
        runner = FakeRunner(env)
        assert run(tmp_path, env, runner) == ra.EXIT_OK
        assert runner.calls == []
    finally:
        held.close()
    assert rd.acquire_lock(tmp_path / "logs" / rd.LOCK_NAME) is not None


def test_failed_step_writes_failed_marker_and_exit_1(tmp_path):
    env = make_env(tmp_path)
    runner = FakeRunner(env, fail=("analyze_before_after",))
    assert run(tmp_path, env, runner) == ra.EXIT_FAILED
    marker = env.out_dir / f"{TARGET}.FAILED.txt"
    text = marker.read_text(encoding="utf-8")
    assert "analyze_before_after FAILED" in text and "chart_before_after NOT RUN" in text
    assert ("rank_daily_top_models", TARGET) in runner.calls  # independent steps continued
    assert run(tmp_path, env, FakeRunner(env)) == ra.EXIT_OK
    assert not marker.exists()


def test_daily_credential_failure_runs_local_steps_and_exits_1(tmp_path):
    env = make_env(tmp_path, with_data=False)

    def expired(tenant: str) -> None:
        raise ra.CredentialError("expired")

    runner = FakeRunner(env)
    assert run(tmp_path, env, runner, expired) == ra.EXIT_FAILED
    names = {n for n, _ in runner.calls}
    assert "build_6001_cohort" not in names and "analyze_before_after" in names
    assert "build_6001_cohort NOT RUN" in (env.out_dir / f"{TARGET}.FAILED.txt").read_text(encoding="utf-8")
