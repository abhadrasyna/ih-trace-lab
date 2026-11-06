"""Cron entry point: refresh the Shaka 6001 analysis for the last complete UTC day, with no arguments needed.

Targets the last complete UTC day D (and the IST day D it overlaps: IST day D runs from UTC D-1 18:30 to UTC D 18:30, so it is
complete once UTC day D is). It backfills any of the ``--lookback-days`` days before D (default from ``config/analysis.yaml``)
whose outputs are missing - cron does not catch up missed runs - then runs the full step registry of ``run_analysis.py`` with
``--fetch-missing`` for the window config start date .. D, so before/after totals, the tenure and trend views stay current.

Runs are one at a time (lock file; a second start logs and exits 0). The log is ``logs/run-daily_<D>.log`` (30-day prune) and
ends with a run summary (OK / FAILED / NOT RUN per step). A failing step does not stop independent steps; any failure or NOT RUN
step writes ``<D>.FAILED.txt`` next to the outputs and exits 1, so a half-built report is never mistaken for a good one (a later
clean run removes the note). AWS SSO is verified through ``src.lib.auth`` before the first Athena call; if that fails the Athena
steps are NOT RUN, the local-data steps still run and the exit code is 1. A fetch estimated above ``--max-scan-gb`` is skipped
with the reason logged. Installing the crontab is a human step; see ``docs/usage.md``.

Usage:
    python investigations/shaka-6001/scripts/run_daily.py
"""
from __future__ import annotations

import argparse
import fcntl
import logging
import sys
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import IO

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT, REPO_ROOT / "vendor" / "athena-mcp-server" / "src"):
    if _path.exists() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.run_analysis import (  # noqa: E402
    DEFAULT_CONFIG_PATH, DEFAULT_STEP_TIMEOUT_MINUTES, EXIT_FAILED, EXIT_OK, REGISTRY,
    CredentialCheck, CredentialGate, RunEnv, RunnerError, RunRequest, Step, StepOutcome, StepRunner,
    StepStatus, build_env, default_end_date, make_subprocess_runner, range_outputs, run_range, select_steps,
    summary_lines, verify_sso,
)
from scripts.lib.analysis_config import AnalysisConfig, AnalysisConfigError, load_config  # noqa: E402
from scripts.lib.local_data import LocalDataError  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.run_daily")
LOG_PREFIX = "run-daily"
LOG_KEEP_DAYS = 30
DEFAULT_LOG_DIR = INVESTIGATION_ROOT / "logs"
LOCK_NAME = "run-daily.lock"


def acquire_lock(path: Path) -> IO[str] | None:
    """Non-blocking exclusive lock; None when another run holds it. The OS drops it if the process dies."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def backfill_dates(target: date, start: date, lookback_days: int, env: RunEnv, steps: Sequence[Step]) -> list[date]:
    """Days before ``target`` inside the lookback window (and not before ``start``) whose expected outputs are not all present."""
    days = [target - timedelta(days=n) for n in range(lookback_days, 0, -1)]
    return [d for d in days if d >= start and any(not p.is_file() for s in steps for p in range_outputs(s, env, start, d))]


def write_marker(out_dir: Path, day: date, problems: Sequence[str]) -> Path:
    path = out_dir / f"{day.isoformat()}.FAILED.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"daily analysis for {day} is incomplete; do not trust its outputs:\n"
                    + "\n".join(f"- {p}" for p in problems) + "\n", encoding="utf-8")
    return path


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--lookback-days", type=int, default=config.daily_lookback_days,
                        help="backfill any of the previous N days whose outputs are missing (default: from config)")
    parser.add_argument("--max-scan-gb", type=float, default=config.max_scan_gb,
                        help="skip a fetch whose estimated scan exceeds this (default: from config)")
    parser.add_argument("--step-timeout-minutes", type=float, default=DEFAULT_STEP_TIMEOUT_MINUTES)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR, help="run-daily_<date>.log and the lock file")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    return parser


def _run_window(target: date, config: AnalysisConfig, args: argparse.Namespace, env: RunEnv, runner: StepRunner,
                gate: CredentialGate) -> list[str]:
    """Backfill runs (oldest first) then the target run; returns one problem line per FAILED / NOT RUN step."""
    steps = select_steps(None, REGISTRY)
    ends = [*backfill_dates(target, config.default_start_date, args.lookback_days, env, steps), target]
    LOGGER.info("daily run: utc_day=%s ist_day=%s (UTC %s 18:30..%s 18:30) window_start=%s run_ends=%s", target, target,
                target - timedelta(days=1), target, config.default_start_date, ",".join(d.isoformat() for d in ends))
    problems: list[str] = []
    for end in ends:
        req = RunRequest(config.default_start_date, end, args.tenant, None, True, args.max_scan_gb,
                         extra_args=("--config", str(args.config), "--paths-config", str(args.paths_config)))
        outcomes: list[StepOutcome] = run_range(req, env, runner, gate) or []
        for line in summary_lines(outcomes, f"{req.start}..{req.end}"):
            LOGGER.log(logging.ERROR if "FAILED" in line or "NOT RUN" in line else logging.INFO, "%s", line)
        problems += [f"{end}: {o.name} {o.status.value}" + (f" ({o.reason})" if o.reason else "")
                     for o in outcomes if o.status is not StepStatus.OK]
    return problems


def main(argv: Sequence[str] | None = None, *, runner: StepRunner | None = None, credential_check: CredentialCheck | None = None,
         env: RunEnv | None = None, now: datetime | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    try:
        config = load_config(pre.parse_known_args(argv)[0].config)
    except AnalysisConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_FAILED
    args = build_parser(config).parse_args(argv)
    if args.lookback_days < 1:
        print("ERROR: --lookback-days must be >= 1", file=sys.stderr)
        return EXIT_FAILED
    target = default_end_date(now)
    fcid = init_logging("shaka-6001-run-daily", log_dir=args.log_dir, file_prefix=LOG_PREFIX, date=target, keep_days=LOG_KEEP_DAYS)
    lock = acquire_lock(args.log_dir / LOCK_NAME)
    if lock is None:
        LOGGER.warning("another run-daily is already running (lock %s); exiting without doing anything", args.log_dir / LOCK_NAME)
        return EXIT_OK
    try:
        run_env = env or build_env(args.paths_config, args.tenant)
        gate = CredentialGate(credential_check or verify_sso)
        run_runner = runner or make_subprocess_runner(args.step_timeout_minutes * 60)
        try:
            if target < config.default_start_date:
                raise RunnerError(f"last complete UTC day {target} is before the config start date {config.default_start_date}")
            problems = _run_window(target, config, args, run_env, run_runner, gate)
        except (RunnerError, LocalDataError) as exc:
            LOGGER.error("run-daily failed: %s", exc)
            problems = [str(exc)]
        if problems:
            marker = write_marker(run_env.out_dir, target, problems)
            LOGGER.error("daily run FAILED (%d problem(s)); wrote %s; fcid=%s", len(problems), marker, fcid)
            return EXIT_FAILED
        (run_env.out_dir / f"{target.isoformat()}.FAILED.txt").unlink(missing_ok=True)
        LOGGER.info("daily run OK for %s", target)
        return EXIT_OK
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
