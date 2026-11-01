"""Cron-ready daily chain for one UTC day: Lightstep export, input check, pipeline, 1xxx error report, household ranking.

Steps, in order (each a subprocess run from ``investigations/ctap-smvod/``, one FCID for the whole run):
  1. ``export_lightstep_day.py --tenant T --date YYYY-MM-DD`` for every tenant (skip with ``--skip-export``)
  2. ``check_lightstep_inputs.py --date DDMMYYYY --drm``
  3. ``run_pipeline.py --date DDMMYYYY --drm --skip-input-check``
  4. ``extract_error_report_1xxx.py --date DDMMYYYY --tenants ...``
  5. ``rank_households_by_error.py --csv output/T/YYYY-MM-DD_error_report_1xxx.csv --top N`` per tenant

The first failed step stops the run; ranking continues across tenants. Exit code is non-zero if any step failed or an expected
output CSV is missing. Steps 3/4 of ``run_pipeline.py`` need AWS SSO: its pre-flight refreshes through ``aws-sso`` and fails fast
(non-zero exit, logged here) when the session cannot be refreshed non-interactively.

Usage:
    python3 run_daily_pipeline.py                       # yesterday UTC, ZA,GH,ZM
    python3 run_daily_pipeline.py --date 29102026 --skip-export
Crontab (13:00 IST daily, UTC day just ended):
    0 13 * * * cd <repo> && .venv/bin/python investigations/ctap-smvod/scripts/run_daily_pipeline.py >> investigations/ctap-smvod/logs/cron.out 2>&1
Cron's PATH is minimal: set ``PATH`` (with ``aws``/``aws-sso``) at the top of the crontab.
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import current_fcid

LOGGER = logging.getLogger(__name__)
LOG_PREFIX = "run-daily-pipeline"
LOG_KEEP_DAYS = 30
INVESTIGATION_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = INVESTIGATION_DIR / "scripts"
DEFAULT_LOG_DIR = INVESTIGATION_DIR / "logs"
DEFAULT_TENANTS = ("ZA", "GH", "ZM")
FCID_ENV = "FCID"
DEFAULT_STEP_TIMEOUT_MINUTES = 180

# (return code, combined stdout+stderr)
StepRunner = Callable[[Sequence[str], Path, dict[str, str]], tuple[int, str]]


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]
    outputs: tuple[Path, ...] = ()
    continue_on_failure: bool = False


@dataclass(frozen=True)
class StepResult:
    name: str
    ok: bool
    seconds: float


def parse_day(text: str) -> Date:
    """Accepts ``DDMMYYYY`` (like the sibling scripts) or ``YYYY-MM-DD``."""
    for fmt in ("%d%m%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {text!r}; use DDMMYYYY or YYYY-MM-DD")


def default_day(now: datetime | None = None) -> Date:
    """Yesterday in UTC."""
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date() - timedelta(days=1)


def build_steps(day: Date, tenants: Sequence[str], *, skip_export: bool, top: int, python: str = sys.executable,
                investigation_dir: Path = INVESTIGATION_DIR) -> list[Step]:
    """The ordered step list for ``day``; pure, so it can be tested without running anything."""
    scripts = investigation_dir / "scripts"
    iso, ddmmyyyy = day.isoformat(), day.strftime("%d%m%Y")
    steps: list[Step] = []
    if not skip_export:
        steps += [Step(f"export {t}", (python, str(scripts / "export_lightstep_day.py"), "--tenant", t, "--date", iso)) for t in tenants]
    reports = {t: investigation_dir / "output" / t / f"{iso}_error_report_1xxx.csv" for t in tenants}
    steps += [
        Step("check inputs", (python, str(scripts / "check_lightstep_inputs.py"), "--date", ddmmyyyy, "--drm")),
        Step("run_pipeline", (python, str(scripts / "run_pipeline.py"), "--date", ddmmyyyy, "--drm", "--skip-input-check")),
        Step("error report 1xxx", (python, str(scripts / "extract_error_report_1xxx.py"), "--date", ddmmyyyy, "--tenants", ",".join(tenants)),
             outputs=tuple(reports.values())),
    ]
    steps += [
        Step(f"rank households {t}", (python, str(scripts / "rank_households_by_error.py"), "--csv", str(reports[t]), "--top", str(top)),
             outputs=(reports[t],), continue_on_failure=True)
        for t in tenants
    ]
    return steps


def make_subprocess_runner(timeout_seconds: float) -> StepRunner:
    """A runner that kills a step after ``timeout_seconds`` so a hung step cannot block the next day's cron run."""

    def runner(argv: Sequence[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        # Own session so a timeout can kill the whole process group (aws-sso, Athena children), not just the script.
        proc = subprocess.Popen(list(argv), cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            output, _ = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
            return 124, f"{output or ''}\ntimed out after {timeout_seconds:.0f}s"
        return proc.returncode, output or ""

    return runner


def run_steps(steps: Sequence[Step], run: StepRunner, *, cwd: Path, env: dict[str, str]) -> list[StepResult]:
    """Runs steps in order; stops after the first failure unless the step allows continuing."""
    results: list[StepResult] = []
    for step in steps:
        LOGGER.info("step start: %s", step.name)
        started = time.monotonic()
        code, output = run(step.argv, cwd, env)
        seconds = time.monotonic() - started
        for line in output.splitlines():
            LOGGER.info("[%s] %s", step.name, line)
        missing = [p for p in step.outputs if code == 0 and not p.is_file()]
        ok = code == 0 and not missing
        LOGGER.log(logging.INFO if ok else logging.ERROR, "step end: %s exit=%d duration=%.1fs%s", step.name, code, seconds,
                   f" missing output(s): {', '.join(map(str, missing))}" if missing else "")
        results.append(StepResult(step.name, ok, seconds))
        if not ok and not step.continue_on_failure:
            LOGGER.error("stopping: step %r failed", step.name)
            break
    return results


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None, help="UTC day as DDMMYYYY or YYYY-MM-DD (default: yesterday UTC)")
    ap.add_argument("--tenants", default=",".join(DEFAULT_TENANTS), help="Comma-separated tenant codes (default: ZA,GH,ZM)")
    ap.add_argument("--skip-export", action="store_true", help="Skip the Lightstep export; use CSVs already in data/lightstep/<TENANT>/")
    ap.add_argument("--top", type=int, default=10, help="Households to print per tenant in the ranking (default: 10)")
    ap.add_argument("--step-timeout-minutes", type=float, default=DEFAULT_STEP_TIMEOUT_MINUTES,
                    help=f"Kill any single step after this many minutes (default: {DEFAULT_STEP_TIMEOUT_MINUTES:g})")
    ap.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR, help="Folder for run-daily-pipeline_<date>.log (default: investigations/ctap-smvod/logs)")
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None, runner: StepRunner | None = None) -> int:
    args = parse_args(argv)
    try:
        day = parse_day(args.date) if args.date else default_day()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    tenants = [t.strip().upper() for t in args.tenants.split(",") if t.strip()]
    if not tenants:
        print("ERROR: --tenants is empty", file=sys.stderr)
        return 1
    fcid = init_logging("run-daily-pipeline", log_dir=args.log_dir, file_prefix=LOG_PREFIX, date=day, keep_days=LOG_KEEP_DAYS)
    LOGGER.info("daily pipeline for %s tenants=%s skip_export=%s fcid=%s", day.isoformat(), ",".join(tenants), args.skip_export, current_fcid())
    steps = build_steps(day, tenants, skip_export=args.skip_export, top=args.top, investigation_dir=INVESTIGATION_DIR)
    results = run_steps(steps, runner or make_subprocess_runner(args.step_timeout_minutes * 60), cwd=INVESTIGATION_DIR, env={**os.environ, FCID_ENV: fcid})
    failed = [r.name for r in results if not r.ok]
    not_run = len(steps) - len(results)
    if failed or not_run:
        LOGGER.error("daily pipeline FAILED: failed=%s not_run=%d", failed, not_run)
        return 1
    LOGGER.info("daily pipeline OK: %d steps", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
