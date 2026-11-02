"""Cron-ready daily chain for one UTC day: Lightstep export, input check, pipeline, 1xxx error report, household ranking.

Steps, in order (each a subprocess run from ``investigations/ctap-smvod/``, one FCID for the whole run):
  1. ``export_lightstep_day.py --tenant T --date YYYY-MM-DD`` for every tenant (skip with ``--skip-export``)
  2. ``check_lightstep_inputs.py --date DDMMYYYY --drm``
  3. ``run_pipeline.py --date DDMMYYYY --drm --skip-input-check``
  4. ``extract_error_report_1xxx.py --date DDMMYYYY --tenants ...``
  5. ``rank_households_by_error.py --csv output/T/YYYY-MM-DD_error_report_1xxx.csv --top N`` per tenant
  6. (opt-in ``--ebvs-release-coverage``) ``analyze_ebvs_release_coverage.py`` per tenant for the day ``--coverage-lag-days`` (default 1) before the run day,
     so the next day's Release file exists; a tenant whose inputs for that day are missing is skipped with a warning (never a failure)

The log ends with a summary: OK / FAILED / NOT RUN / SKIPPED per step and the exact command to resume.

The first failed step stops the run, except: an export whose CSVs were all written (e.g. only the input check failed), the advisory
input-check step, and the per-tenant ranking all let the run continue; the final exit is still non-zero. Exit code is non-zero if any step failed or an expected
output CSV is missing. Steps 3/4 of ``run_pipeline.py`` need AWS SSO: its pre-flight refreshes through ``aws-sso`` and fails fast
(non-zero exit, logged here) when the session cannot be refreshed non-interactively.

Usage:
    python3 run_daily_pipeline.py                       # yesterday UTC, ZA,GH,ZM
    python3 run_daily_pipeline.py --date 29102026 --skip-export
    python3 run_daily_pipeline.py --date 29102026 --from-step pipeline   # resume after a failure (export, check, pipeline, report, rank)
    python3 run_daily_pipeline.py --date 30102026 --skip-export --table-suffix oct26 --force   # past-month day: read <id>_ccl_debug_events_oct26
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

from lib.tenant_context import add_table_suffix_arg
from scripts.lib.lightstep_export_kinds import KINDS, output_file_name
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
# --from-step group -> prefix of the step names it starts at
STEP_GROUPS = {"export": "export ", "check": "check inputs", "pipeline": "run_pipeline", "report": "error report", "rank": "rank households",
               "coverage": "ebvs release coverage"}

# (return code, combined stdout+stderr)
StepRunner = Callable[[Sequence[str], Path, dict[str, str]], tuple[int, str]]


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]
    outputs: tuple[Path, ...] = ()
    continue_on_failure: bool = False
    continue_if_outputs_exist: bool = False


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


def build_steps(day: Date, tenants: Sequence[str], *, skip_export: bool, top: int, workers: int | None = None, python: str = sys.executable,
                investigation_dir: Path = INVESTIGATION_DIR, table_suffix: str | None = None, force: bool = False) -> list[Step]:
    """The ordered step list for ``day``; pure, so it can be tested without running anything."""
    scripts = investigation_dir / "scripts"
    iso, ddmmyyyy = day.isoformat(), day.strftime("%d%m%Y")
    steps: list[Step] = []
    if not skip_export:
        extra = ("--workers", str(workers)) if workers is not None else ()
        steps += [
            Step(f"export {t}", (python, str(scripts / "export_lightstep_day.py"), "--tenant", t, "--date", iso, *extra),
                 outputs=tuple(investigation_dir / "data" / "lightstep" / t / output_file_name(k, iso) for k in KINDS), continue_if_outputs_exist=True)
            for t in tenants
        ]
    reports = {t: investigation_dir / "output" / t / f"{iso}_error_report_1xxx.csv" for t in tenants}
    pipeline_extra = (("--table-suffix", table_suffix) if table_suffix else ()) + (("--force",) if force else ())
    steps += [
        Step("check inputs", (python, str(scripts / "check_lightstep_inputs.py"), "--date", ddmmyyyy, "--drm"), continue_on_failure=True),
        Step("run_pipeline", (python, str(scripts / "run_pipeline.py"), "--date", ddmmyyyy, "--drm", "--skip-input-check", *pipeline_extra)),
        Step("error report 1xxx", (python, str(scripts / "extract_error_report_1xxx.py"), "--date", ddmmyyyy, "--tenants", ",".join(tenants)),
             outputs=tuple(reports.values())),
    ]
    steps += [
        Step(f"rank households {t}", (python, str(scripts / "rank_households_by_error.py"), "--csv", str(reports[t]), "--top", str(top)),
             outputs=(reports[t],), continue_on_failure=True)
        for t in tenants
    ]
    return steps


def coverage_plan(day: Date, tenants: Sequence[str], lag_days: int, *, python: str = sys.executable,
                  investigation_dir: Path = INVESTIGATION_DIR) -> tuple[list[Step], list[str]]:
    """EBVS Release-coverage steps for ``day - lag_days`` plus a reason per tenant skipped for missing inputs."""
    target = day - timedelta(days=lag_days)
    iso = target.isoformat()
    steps: list[Step] = []
    skipped: list[str] = []
    for tenant in tenants:
        needed = [investigation_dir / "data" / "athena" / tenant / f"{iso}_session.csv",
                  *(investigation_dir / "data" / "lightstep" / tenant / output_file_name(k, iso) for k in ("smvod", "smvod-release"))]
        missing = [p.name for p in needed if not p.is_file()]
        if missing:
            skipped.append(f"ebvs release coverage {tenant} ({iso}): missing {', '.join(missing)}")
            continue
        steps.append(Step(f"ebvs release coverage {tenant}",
                          (python, str(investigation_dir / "scripts" / "analyze_ebvs_release_coverage.py"), "--date", iso, "--tenant", tenant),
                          outputs=(investigation_dir / "output" / tenant / f"{iso}_ebvs_release_coverage.csv",), continue_on_failure=True))
    return steps, skipped


def format_summary(steps: Sequence[Step], results: Sequence[StepResult], skipped: Sequence[str], day: Date, *, extra_flags: str = "") -> list[tuple[int, str]]:
    """Closing log lines as (level, text): per-step status, then what to resume. Pure."""
    by_name = {r.name: r for r in results}
    lines: list[tuple[int, str]] = [(logging.INFO, "==== run summary ====")]
    redo: list[Step] = []
    for step in steps:
        result = by_name.get(step.name)
        if result is None:
            status = "NOT RUN"
        else:
            status = f"OK ({result.seconds:.1f}s)" if result.ok else f"FAILED ({result.seconds:.1f}s)"
        if result is None or not result.ok:
            redo.append(step)
        lines.append((logging.INFO if status.startswith("OK") else logging.ERROR, f"  {step.name}: {status}"))
    lines += [(logging.WARNING, f"  SKIPPED {reason}") for reason in skipped]
    if not redo and not skipped:
        lines.append((logging.INFO, "nothing to resume"))
        return lines
    if redo:
        group = next((g for g, prefix in STEP_GROUPS.items() if redo[0].name.startswith(prefix)), "export")
        advisory = all(s.continue_on_failure for s in redo) and all(s.name in by_name for s in redo)
        lines.append((logging.ERROR, f"to resume: python3 run_daily_pipeline.py --date {day.strftime('%d%m%Y')} --from-step {group}{extra_flags}"
                      + ("  (only advisory steps failed; the main chain completed)" if advisory else "")))
    if skipped:
        lines.append((logging.WARNING, "skipped coverage steps run once their inputs exist: --from-step coverage --ebvs-release-coverage"))
    return lines


def select_from_step(steps: Sequence[Step], from_step: str | None) -> list[Step]:
    """Drops every step before the first one in group ``from_step`` (``None`` keeps all)."""
    if from_step is None:
        return list(steps)
    prefix = STEP_GROUPS[from_step]
    for index, step in enumerate(steps):
        if step.name.startswith(prefix):
            return list(steps[index:])
    raise ValueError(f"no step in group {from_step!r} (is --skip-export hiding it?)")


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
        keep_going = step.continue_on_failure or (step.continue_if_outputs_exist and all(p.is_file() for p in step.outputs))
        if not ok and keep_going:
            LOGGER.warning("step %r failed but the run continues (outputs present or step is advisory); final exit will be non-zero", step.name)
        if not ok and not keep_going:
            LOGGER.error("stopping: step %r failed", step.name)
            break
    return results


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None, help="UTC day as DDMMYYYY or YYYY-MM-DD (default: yesterday UTC)")
    ap.add_argument("--tenants", default=",".join(DEFAULT_TENANTS), help="Comma-separated tenant codes (default: ZA,GH,ZM)")
    ap.add_argument("--skip-export", action="store_true", help="Skip the Lightstep export; use CSVs already in data/lightstep/<TENANT>/")
    ap.add_argument("--from-step", choices=list(STEP_GROUPS), default=None,
                    help="Resume: skip every step before this one (export, check, pipeline, report, rank); use after a failure")
    ap.add_argument("--ebvs-release-coverage", action="store_true",
                    help="Add the EBVS Release-coverage analysis for the day --coverage-lag-days back (implied by --from-step coverage)")
    ap.add_argument("--coverage-lag-days", type=int, default=1, choices=range(1, 8), metavar="1-7",
                    help="Days before the run day to analyse, so the next day's Release file exists (default: 1)")
    ap.add_argument("--workers", type=int, default=None, choices=range(1, 9), metavar="1-8",
                    help="Passed to export_lightstep_day.py --workers (default: the exporter's own default, 4)")
    add_table_suffix_arg(ap)
    ap.add_argument("--force", action="store_true", help="Passed to run_pipeline.py: re-run Athena even if the output CSVs already have data")
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
    if args.table_suffix is None and (day.year, day.month) != (datetime.now(timezone.utc).year, datetime.now(timezone.utc).month):
        LOGGER.warning("%s is not in the current UTC month and no --table-suffix was given: the unsuffixed debug table may lack that day's data", day.isoformat())
    steps = build_steps(day, tenants, skip_export=args.skip_export, top=args.top, workers=args.workers, investigation_dir=INVESTIGATION_DIR,
                        table_suffix=args.table_suffix, force=args.force)
    skipped: list[str] = []
    coverage = args.ebvs_release_coverage or args.from_step == "coverage"
    if coverage:
        extra, skipped = coverage_plan(day, tenants, args.coverage_lag_days, investigation_dir=INVESTIGATION_DIR)
        steps += extra
        if args.from_step == "coverage" and not extra:
            for reason in skipped:
                LOGGER.warning("SKIPPED %s", reason)
            LOGGER.error("--from-step coverage: no tenant has its coverage inputs; nothing to run")
            return 1
    try:
        steps = select_from_step(steps, args.from_step)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1
    results = run_steps(steps, runner or make_subprocess_runner(args.step_timeout_minutes * 60), cwd=INVESTIGATION_DIR, env={**os.environ, FCID_ENV: fcid})
    flags = (" --ebvs-release-coverage" if coverage else "") + (" --skip-export" if args.skip_export else "")
    flags += f" --coverage-lag-days {args.coverage_lag_days}" if coverage and args.coverage_lag_days != 1 else ""
    flags += f" --tenants {','.join(tenants)}" if tenants != list(DEFAULT_TENANTS) else ""
    flags += (f" --table-suffix {args.table_suffix}" if args.table_suffix else "") + (" --force" if args.force else "")
    for level, text in format_summary(steps, results, skipped, day, extra_flags=flags):
        LOGGER.log(level, "%s", text)
    failed = [r.name for r in results if not r.ok]
    not_run = len(steps) - len(results)
    if failed or not_run:
        LOGGER.error("daily pipeline FAILED: failed=%s not_run=%d", failed, not_run)
        return 1
    LOGGER.info("daily pipeline OK: %d steps", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
