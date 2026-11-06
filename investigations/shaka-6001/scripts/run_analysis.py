"""Run the Shaka 6001 analysis scripts for a date range, in dependency order, from a registry of named steps.

Each step is one existing script run as a subprocess with the same ``--start-date/--end-date/--tenant``. A new analysis
registers itself with ``register(Step(...))``; the runner never grows a branch per script. Re-running a range overwrites
that range's outputs (every script is idempotent).

Local data first: before any step runs, the dates of the fetchable inputs (playback-outcome sessions for
``build_6001_cohort``, guest-login redirect and debug files for ``fetch_guest_login_redirects``) that exist in no local
source are reported. Unless ``--fetch-missing`` is given the run stops there, before any Athena query. With the flag, AWS
SSO is verified once through ``src.lib.auth`` before the first Athena step; if that fails the Athena steps (and the steps that
need their output) are NOT RUN while the local-data steps still run, and the exit code is 1. A step whose fetch would scan more
than ``--max-scan-gb`` is skipped (NOT RUN) with the reason logged. A failed step blocks only the steps that need its output.
Missing dates of inputs that cannot be fetched here (the 6001 error events) are reported as warnings only.

Usage:
    python scripts/run_analysis.py --end-date 2026-11-05                      # local data only; stops if fetchable dates are missing
    python scripts/run_analysis.py --end-date 2026-11-05 --fetch-missing      # fetch what is missing, then analyse
    python scripts/run_analysis.py --end-date 2026-11-05 --only analyze_before_after,chart_before_after
    python scripts/run_analysis.py --end-date 2026-11-05 --dry-run            # print the plan; no steps, no credentials
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT, REPO_ROOT / "vendor" / "athena-mcp-server" / "src"):
    if _path.exists() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, AnalysisConfigError, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, find_daily_file  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.run_analysis")
SCRIPTS_DIR = INVESTIGATION_ROOT / "scripts"
DEFAULT_STEP_TIMEOUT_MINUTES = 120
FCID_ENV = "FCID"

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


class RunnerError(Exception):
    """Raised for an unusable runner request (unknown step, bad range, dependency cycle)."""


class CredentialError(RunnerError):
    """Raised when AWS SSO cannot be verified or refreshed non-interactively."""


class StepStatus(str, Enum):
    OK = "OK"
    FAILED = "FAILED"
    NOT_RUN = "NOT RUN"


@dataclass(frozen=True)
class Need:
    """A daily input file ``<date>_<artifact>.csv``; ``all_sources`` False means only this investigation's data folder."""
    artifact: str
    all_sources: bool = True


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    depends_on: tuple[str, ...] = ()  # needs these steps' output: NOT RUN when one did not succeed
    after: tuple[str, ...] = ()  # ordering only: runs even when these did not succeed
    athena: bool = False  # may query Athena (only when ``fetches`` has missing dates)
    fetches: tuple[Need, ...] = ()  # daily inputs this step fetches when missing
    reads: tuple[Need, ...] = ()  # daily inputs it cannot fetch; missing dates are only reported
    scan_mb_per_date: int = 0  # estimated Athena scan per missing date, for the cost guard
    outputs: tuple[str, ...] = ()  # range artifacts (``<start>_<end>_<artifact>.csv``) that must exist after a successful run


@dataclass(frozen=True)
class RunEnv:
    resolver: YamlPathResolver
    sources: tuple[Path, ...]  # lookup order; the first is this investigation's own data folder
    out_dir: Path


@dataclass(frozen=True)
class RunRequest:
    start: date
    end: date
    tenant: str
    only: tuple[str, ...] | None = None
    fetch_missing: bool = False
    max_scan_gb: float = 10.0
    extra_args: tuple[str, ...] = ()  # e.g. --config/--paths-config passthrough


@dataclass(frozen=True)
class StepOutcome:
    name: str
    status: StepStatus
    seconds: float = 0.0
    reason: str = ""


StepRunner = Callable[[Sequence[str], Path, Mapping[str, str]], tuple[int, str]]
CredentialCheck = Callable[[str], None]

REGISTRY: dict[str, Step] = {}


def register(step: Step, registry: dict[str, Step] | None = None) -> Step:
    target = REGISTRY if registry is None else registry
    if step.name in target:
        raise RunnerError(f"step already registered: {step.name}")
    target[step.name] = step
    return step


_SESSION = Need("session")
_GUEST_DATA = (Need("guest_login_redirect", all_sources=False), Need("guest_redirect_debug_events", all_sources=False))

register(Step("build_enriched_events", "build_enriched_events.py", reads=(Need("error_eventdata_codes-6001"),),
              outputs=("shaka6001_enriched",)))
register(Step("analyze_before_after", "analyze_before_after.py", depends_on=("build_enriched_events",),
              outputs=("6001_before_after_webview", "6001_before_after_model")))
register(Step("analyze_versions_devices", "analyze_versions_devices.py", depends_on=("build_enriched_events",),
              after=("build_6001_cohort",), outputs=("6001_by_chrome", "6001_by_android")))
register(Step("chart_before_after", "chart_before_after.py", depends_on=("analyze_before_after",),
              after=("analyze_versions_devices",)))
register(Step("fetch_guest_login_redirects", "fetch_guest_login_redirects.py", athena=True, fetches=_GUEST_DATA,
              scan_mb_per_date=650))
register(Step("analyze_guest_login_redirects", "analyze_guest_login_redirects.py", after=("fetch_guest_login_redirects",)))
register(Step("build_6001_cohort", "build_6001_cohort.py", depends_on=("build_enriched_events",), athena=True,
              fetches=(_SESSION,), scan_mb_per_date=1000, outputs=("6001_cohort",)))
register(Step("analyze_6001_recovery", "analyze_6001_recovery.py", depends_on=("build_6001_cohort",),
              outputs=("6001_recovery_members", "6001_recovery_summary")))
register(Step("rank_daily_top_impacted", "rank_daily_top_impacted.py", depends_on=("build_enriched_events",),
              after=("analyze_6001_recovery",)))
register(Step("rank_daily_top_models", "rank_daily_top_models.py", depends_on=("build_enriched_events",)))
register(Step("analyze_user_tenure", "analyze_user_tenure.py", after=("build_6001_cohort",),
              outputs=("user_tenure_households", "user_tenure_buckets")))


def select_steps(only: Sequence[str] | None, registry: Mapping[str, Step]) -> list[Step]:
    """The named steps (all when ``only`` is empty), in dependency order; unselected dependencies are assumed built earlier."""
    names = list(registry) if not only else list(dict.fromkeys(only))
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise RunnerError(f"unknown step(s): {', '.join(unknown)}; known: {', '.join(registry)}")
    return order_steps([registry[n] for n in names])


def order_steps(steps: Sequence[Step]) -> list[Step]:
    """Topological order over ``depends_on`` and ``after`` among the given steps; ties keep registry order."""
    chosen = {s.name: s for s in steps}
    ordered: list[Step] = []
    placed: set[str] = set()
    pending = list(steps)
    while pending:
        ready = next((s for s in pending if all(d in placed or d not in chosen for d in (*s.depends_on, *s.after))), None)
        if ready is None:
            raise RunnerError("dependency cycle among steps: " + ", ".join(s.name for s in pending))
        ordered.append(ready)
        placed.add(ready.name)
        pending.remove(ready)
    return ordered


def _needs_missing(needs: Sequence[Need], env: RunEnv, dates: Sequence[date]) -> dict[str, list[date]]:
    found: dict[str, list[date]] = {}
    for need in needs:
        sources = env.sources if need.all_sources else env.sources[:1]
        gaps = [d for d in dates if find_daily_file(sources, d, need.artifact) is None]
        if gaps:
            found[need.artifact] = gaps
    return found


def missing_fetchable(step: Step, env: RunEnv, dates: Sequence[date]) -> dict[str, list[date]]:
    return _needs_missing(step.fetches, env, dates)


def estimate_scan_mb(step: Step, missing: Mapping[str, Sequence[date]]) -> int:
    """Per-date estimate: one scan per distinct missing date (a date missing in several artifacts is fetched once per step)."""
    return len({d for gaps in missing.values() for d in gaps}) * step.scan_mb_per_date


def range_outputs(step: Step, env: RunEnv, start: date, end: date) -> list[Path]:
    return [env.out_dir / env.resolver.format_range_filename(start, end, artifact) for artifact in step.outputs]


def build_argv(step: Step, req: RunRequest, python: str = sys.executable) -> list[str]:
    return [python, str(SCRIPTS_DIR / step.script), "--start-date", req.start.isoformat(), "--end-date", req.end.isoformat(),
            "--tenant", req.tenant, *req.extra_args]


def make_subprocess_runner(timeout_seconds: float) -> StepRunner:
    """Runs a step in its own session so a timeout kills the whole process group, not just the script."""

    def runner(argv: Sequence[str], cwd: Path, env: Mapping[str, str]) -> tuple[int, str]:
        proc = subprocess.Popen(list(argv), cwd=cwd, env=dict(env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        try:
            output, _ = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
            return 124, f"{output or ''}\ntimed out after {timeout_seconds:.0f}s"
        return proc.returncode, output or ""

    return runner


def verify_sso(tenant: str) -> None:
    """Verify (refresh when possible, never prompt) the AWS SSO session of the tenant's Athena profile."""
    try:
        from athena_runner.aws_clients import AwsClientFactory
        from athena_runner.sso_auth import SsoCredentialRefresher

        from src.lib.auth.sso import SsoAuth
        from src.tenant_registry import AthenaQueryTarget, TenantRegistry

        context = AthenaQueryTarget().build_context(TenantRegistry().get(tenant))
        profile, region = str(context["profile"]), str(context.get("region", "eu-central-1"))
        auth = SsoAuth(
            refresher_factory=lambda name: SsoCredentialRefresher(
                profile=name, sts_client_factory=lambda: AwsClientFactory(name, region=region).sts_client()),
            session_factory=lambda name: AwsClientFactory(name, region=region)._session,
        )
        auth.refresh_if_expired(profile)
    except Exception as exc:  # boundary: boto3/athena_runner/registry errors never leak
        raise CredentialError(f"AWS SSO is not usable for tenant {tenant}: {exc}; run: aws sso login") from exc


@dataclass
class CredentialGate:
    """Verifies SSO at most once per process, lazily at the first Athena step that really has something to fetch."""
    check: CredentialCheck = verify_sso
    _error: CredentialError | None = field(default=None, init=False)
    _checked: bool = field(default=False, init=False)

    def ensure(self, tenant: str) -> None:
        if not self._checked:
            self._checked = True
            try:
                self.check(tenant)
            except CredentialError as exc:
                self._error = exc
                LOGGER.error("%s", exc)
            except Exception as exc:  # an injected check may raise anything; the gate reports it as one error
                self._error = CredentialError(f"credential check failed: {exc}")
                LOGGER.error("%s", self._error)
        if self._error is not None:
            raise self._error


def report_missing(steps: Sequence[Step], env: RunEnv, dates: Sequence[date]) -> dict[str, dict[str, list[date]]]:
    """Fetchable gaps per step, logged up front; gaps of unfetchable inputs are warnings only."""
    fetchable: dict[str, dict[str, list[date]]] = {}
    for step in steps:
        for artifact, gaps in _needs_missing(step.reads, env, dates).items():
            LOGGER.warning("%s: no local %s for %s (cannot be fetched by the runner)", step.name, artifact,
                           ",".join(d.isoformat() for d in gaps))
        gaps = missing_fetchable(step, env, dates)
        if gaps:
            fetchable[step.name] = gaps
            for artifact, days in gaps.items():
                LOGGER.warning("%s: missing local %s for %s (~%d MB to fetch)", step.name, artifact,
                               ",".join(d.isoformat() for d in days), estimate_scan_mb(step, {artifact: days}))
    return fetchable


def execute(steps: Sequence[Step], req: RunRequest, env: RunEnv, runner: StepRunner, gate: CredentialGate,
            *, cwd: Path = INVESTIGATION_ROOT, environ: Mapping[str, str] | None = None) -> list[StepOutcome]:
    """Runs ``steps`` (already ordered) once each. A failed step blocks only steps that ``depends_on`` it."""
    dates = date_range(req.start, req.end)
    outcomes: dict[str, StepOutcome] = {}
    for step in steps:
        blocker = next((d for d in step.depends_on if d in {s.name for s in steps} and outcomes[d].status is not StepStatus.OK), None)
        if blocker:
            outcomes[step.name] = _not_run(step, f"needs {blocker}, which is {outcomes[blocker].status.value}")
            continue
        skip = _athena_skip_reason(step, req, env, dates, gate)
        if skip:
            outcomes[step.name] = _not_run(step, skip)
            continue
        outcomes[step.name] = _run_step(step, req, env, runner, cwd, environ or os.environ)
    return [outcomes[s.name] for s in steps]


def _not_run(step: Step, reason: str) -> StepOutcome:
    LOGGER.error("NOT RUN %s: %s", step.name, reason)
    return StepOutcome(step.name, StepStatus.NOT_RUN, reason=reason)


def _athena_skip_reason(step: Step, req: RunRequest, env: RunEnv, dates: Sequence[date], gate: CredentialGate) -> str | None:
    if not step.athena:
        return None
    missing = missing_fetchable(step, env, dates)
    if not missing:
        return None
    if not req.fetch_missing:
        return "missing local dates and --fetch-missing not given"
    scan_mb = estimate_scan_mb(step, missing)
    if scan_mb > req.max_scan_gb * 1024:
        return f"cost guard: estimated scan {scan_mb / 1024:.1f} GB exceeds --max-scan-gb {req.max_scan_gb:g}"
    try:
        gate.ensure(req.tenant)
    except CredentialError as exc:
        return f"credentials: {exc}"
    return None


def _run_step(step: Step, req: RunRequest, env: RunEnv, runner: StepRunner, cwd: Path, environ: Mapping[str, str]) -> StepOutcome:
    argv = build_argv(step, req)
    LOGGER.info("step start: %s", step.name)
    started = time.monotonic()
    code, output = runner(argv, cwd, environ)
    seconds = time.monotonic() - started
    for line in output.splitlines():
        LOGGER.info("[%s] %s", step.name, line)
    absent = [p for p in range_outputs(step, env, req.start, req.end) if code == 0 and not p.is_file()]
    ok = code == 0 and not absent
    LOGGER.log(logging.INFO if ok else logging.ERROR, "step end: %s exit=%d duration=%.1fs%s", step.name, code, seconds,
               f" missing output(s): {', '.join(p.name for p in absent)}" if absent else "")
    if ok:
        return StepOutcome(step.name, StepStatus.OK, seconds)
    return StepOutcome(step.name, StepStatus.FAILED, seconds, f"exit {code}" if code else "missing output(s)")


def summary_lines(outcomes: Sequence[StepOutcome], label: str = "") -> list[str]:
    lines = [f"==== run summary{' ' + label if label else ''} ===="]
    for o in outcomes:
        detail = f" ({o.seconds:.1f}s)" if o.status is not StepStatus.NOT_RUN else f": {o.reason}"
        lines.append(f"  {o.name}: {o.status.value}{detail}")
    return lines


def default_end_date(now: datetime | None = None) -> date:
    """Last complete UTC day; the only place the runner relies on 'today'."""
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date() - timedelta(days=1)


def build_env(paths_config: Path, tenant: str) -> RunEnv:
    resolver = YamlPathResolver.from_file(paths_config, REPO_ROOT)
    return RunEnv(resolver=resolver, sources=tuple(default_sources(resolver, REPO_ROOT, tenant)),
                  out_dir=resolver.resolve_investigation_output_dir(SLUG, tenant=tenant))


def run_range(req: RunRequest, env: RunEnv, runner: StepRunner, gate: CredentialGate,
              registry: Mapping[str, Step] | None = None) -> list[StepOutcome] | None:
    """Select, report gaps and execute. Returns None when the run was stopped up front for missing dates."""
    steps = select_steps(req.only, REGISTRY if registry is None else registry)
    if req.end < req.start:
        raise RunnerError(f"end date {req.end} is before start date {req.start}")
    fetchable = report_missing(steps, env, date_range(req.start, req.end))
    if fetchable and not req.fetch_missing:
        LOGGER.error("stopping before any query: local dates are missing for %s; rerun with --fetch-missing",
                     ", ".join(fetchable))
        return None
    return execute(steps, req, env, runner, gate)


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, default=None, help="default: last complete UTC day")
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--only", default=None, help="comma-separated step names to run (default: all); see --list")
    parser.add_argument("--fetch-missing", action="store_true",
                        help="allow Athena fetches for dates missing locally (default: stop and report them)")
    parser.add_argument("--max-scan-gb", type=float, default=config.max_scan_gb,
                        help="skip a step whose estimated fetch scan exceeds this (default: from config)")
    parser.add_argument("--step-timeout-minutes", type=float, default=DEFAULT_STEP_TIMEOUT_MINUTES)
    parser.add_argument("--dry-run", action="store_true", help="print the plan only; no steps, no credentials")
    parser.add_argument("--list", action="store_true", help="list the registered steps and exit")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    return parser


def main(argv: Sequence[str] | None = None, *, runner: StepRunner | None = None, credential_check: CredentialCheck | None = None,
         env: RunEnv | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-run-analysis")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    try:
        config = load_config(pre.parse_known_args(argv)[0].config)
    except AnalysisConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_USAGE
    args = build_parser(config).parse_args(argv)
    if args.list:
        print("\n".join(REGISTRY))
        return EXIT_OK
    end = args.end_date or default_end_date()
    only = tuple(n.strip() for n in args.only.split(",") if n.strip()) if args.only else None
    req = RunRequest(args.start_date, end, args.tenant, only, args.fetch_missing, args.max_scan_gb,
                     extra_args=("--config", str(args.config), "--paths-config", str(args.paths_config)))
    try:
        run_env = env or build_env(args.paths_config, args.tenant)
        if args.dry_run:
            return _print_plan(req, run_env)
        gate = CredentialGate(credential_check or verify_sso)
        outcomes = run_range(req, run_env, runner or make_subprocess_runner(args.step_timeout_minutes * 60), gate)
    except (RunnerError, LocalDataError, AnalysisConfigError) as exc:
        LOGGER.error("run_analysis failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if outcomes is None:
        print("ERROR: local dates are missing; nothing was fetched or run (use --fetch-missing)", file=sys.stderr)
        return EXIT_USAGE
    for line in summary_lines(outcomes, f"{req.start}..{req.end}"):
        print(line)
    return EXIT_OK if all(o.status is StepStatus.OK for o in outcomes) else EXIT_FAILED


def _print_plan(req: RunRequest, env: RunEnv) -> int:
    steps = select_steps(req.only, REGISTRY)
    dates = date_range(req.start, req.end)
    print(f"plan tenant={req.tenant} range={req.start}..{req.end} fetch_missing={req.fetch_missing}")
    for step in steps:
        missing = missing_fetchable(step, env, dates)
        note = f" fetch_dates={sorted({d.isoformat() for g in missing.values() for d in g})} ~{estimate_scan_mb(step, missing)} MB" if missing else ""
        print(f"  {step.name}{note}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
