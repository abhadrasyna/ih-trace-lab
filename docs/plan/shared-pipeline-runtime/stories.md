# Shared pipeline runtime — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `PYTHON_DESIGN.md`, `docs/refactor/design-principles.md` and this
> project's own standards docs. After each task: set `SHA:` on the task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

All code goes under `src/lib/pipeline_runtime/` (every new package dir needs an `__init__.py`). Tests are offline: no Athena, no AWS, no network, no real subprocess except a trivial `python -c` in the
one runner test. Consumers (AAH, LX) change in their own tasks; this story never edits their report logic.

---

## SPR-1 — Audit and design review (docs only)

**Files to change / create:**
- `docs/plan/shared-pipeline-runtime/design.md` (new, no checkboxes) — the audit table, the before diagram and the approved unit contract.
- `docs/plan/lightstep-daily-export-automation/tasks.md`, `stories.md` and `docs/plan/pipeline-migration/aws-access-cli-hardening/tasks.md`, `stories.md` — only if the review changes a task.

**What to implement:**

1. Audit (`code-deduplication-and-taxonomy.md` Step 1): list, per concern, the current implementation in `schedule.py`, `run_daily_pipeline.py`, `run_pipeline._run_tenant`, `lightstep_parallel.py` and
   the two SSO builders, and what each lacks.
2. Draw the before diagram (`architecture-diagrams.md`) and the target one: `Unit` (id, tenant, group, argv-or-callable, outputs, policy) → `run_units(units, runner, policy)` → `UnitResult` list →
   `RunSummary` → status file.
3. Fix the contract: `Unit` is a frozen dataclass table; `UnitRunner` is a `Protocol` (`__call__(unit) -> RunOutcome`); policies (`continue_on_failure`, `continue_if_outputs_exist`, per-unit timeout,
   retry-on-predicate) are data, not subclasses; statuses are `ok|failed|timed_out|skipped`.
4. Decide, and record, whether AAH sub-reports run in-process (thread timeout cannot kill the Athena poll, AAH-3's documented limit; keeps one Athena client per tenant for AAH-10) or as subprocesses
   (real kill, per-unit isolation, one interpreter start per unit). Recommendation: keep in-process for AAH, subprocess for LX; the runner Protocol makes this a per-consumer choice.
5. Fix the status-file schema (see SPR-2) so LX-18 and the AAH alerting read the same JSON.

**Tests:** none (docs). **Review:** the user approves `design.md` before SPR-2 starts.

**Commit:** `docs(plan): shared pipeline runtime design and audit`

---

## SPR-2 — Core: units, runners, summary, status file

**Files to change / create:**
- `src/lib/pipeline_runtime/units.py` — `Unit`, `UnitResult`, `Status`, `RunSummary` (`exit_code`, `failed`, `to_dict()`); pure.
- `src/lib/pipeline_runtime/runner.py` — `UnitRunner` Protocol; `run_units(units, runner, *, log)` (the Template Method: log start/end, verify declared outputs, apply continue/stop policy);
  `make_subprocess_runner(timeout_s)` moved from `run_daily_pipeline.py` (own session, `killpg`, exit 124); `make_inprocess_runner(timeout_s)` (worker thread, `future.result(timeout=…)`, converts
  `SystemExit` and exceptions to `UnitResult`, the logic now in `schedule.run_for_all_tenants`).
- `src/lib/pipeline_runtime/status_file.py` — `write_status(summary, path)` atomic (temp file + `os.replace`), fcid, start/end, units list; `read_status(path)`.
- `tests/lib/pipeline_runtime/` — new.

**What to implement:**

1. Move behaviour, not names: the daily wrapper's loop and `make_subprocess_runner` become the shared ones byte-for-byte in logging and exit codes; the daily wrapper keeps passing its own tests via
   LX-19.
2. FCID is read from the environment/logging context inside worker threads and passed through `env` for subprocesses (`logging-and-correlation-id.md`).
3. Status JSON: `{"fcid","started","finished","exit_code","units":[{"id","tenant","group","status","exit_code","seconds","error"}]}`.

**Tests (no network, no real external services):**
- `test_run_units_stops_after_failure_unless_policy_continues`.
- `test_missing_declared_output_marks_unit_failed`.
- `test_inprocess_runner_converts_systemexit_and_exception_to_failed`.
- `test_inprocess_timeout_marks_timed_out_and_run_continues`.
- `test_subprocess_runner_kills_on_timeout` (one trivial `python -c "import time; time.sleep(60)"`, 1 s limit).
- `test_status_file_is_atomic_and_round_trips`.
- `test_exit_code_is_nonzero_when_any_unit_failed`.

**Commit:** `feat(lib): add pipeline_runtime units, runner and status file`

---

## SPR-3 — SSO pre-flight with rate-limited re-check

**Files to change / create:**
- `src/lib/pipeline_runtime/preflight.py` — `Preflight(refresh: Callable[[], None], *, min_interval_s)`: `ensure()` runs once per run and never raises a traceback (returns `PreflightResult`);
  `recheck()` is allowed once per interval and thread-safe. The AWS-specific `refresh` is injected by consumers over `src.lib.auth.sso.SsoAuth`; the module imports no `athena_runner`.
- `run_units` accepts an optional `retry_if: Callable[[UnitResult], bool]`, used with `recheck()` to retry a unit once after an auth error.
- tests.

**What to implement:** a failed pre-flight returns a result that `run_units` converts to every unit `skipped` and exit 1; a unit whose error matches `retry_if` triggers one `recheck()` and one retry;
other errors are never retried.

**Tests:** `test_failed_preflight_skips_all_units_without_traceback`, `test_auth_error_triggers_one_recheck_and_one_retry`, `test_recheck_is_rate_limited_across_threads`,
`test_non_auth_error_is_not_retried`.

**Commit:** `feat(lib): add run-level preflight with rate-limited recheck`

---

## SPR-4 — Bounded deterministic unit pool

**Files to change / create:**
- `src/lib/pipeline_runtime/pool.py` — `run_pool(groups, run_group, *, max_workers, cap: Semaphore | None)`; `groups` are per-tenant unit lists; results come back in input order. Reuse or re-export
  the `JobRunner` Protocol and `Serial`/`Thread` runners from `scripts/lib/lightstep_parallel.py` (move the module here, leave a re-export shim so LX-10 callers keep working).
- tests.

**What to implement:** `max_workers=1` equals the serial path; one group's failure cancels nothing; a semaphore caps concurrent Athena-using units across groups; FCID present in worker log lines.

**Tests:** `test_results_ordered_by_input_regardless_of_completion`, `test_one_group_failure_does_not_cancel_others`, `test_max_workers_one_matches_serial`, `test_cap_limits_concurrent_units`.

**Commit:** `feat(lib): add bounded deterministic unit pool`

---

## SPR-5 — Artifact registry and prune

**Files to change / create:**
- `src/lib/pipeline_runtime/retention.py` — `Artifact(name, glob, producer, readers, keep_days)` registry type and `plan_prune(artifacts, now)` (pure, returns what would be deleted and why);
  `apply_prune(plan)` deletes only when asked.
- `scripts/prune_artifacts.py` — thin `argparse` CLI: registry module path, `--apply` (default is dry-run). Add the entry to `SCRIPTS.md`.
- tests.

**What to implement:** an artifact with no declared reader and no `keep_days` is reported, never deleted; the dry-run output is a table a human can read before `--apply`; symlinks and paths outside
the registered globs' roots are refused.

**Tests:** `test_dry_run_deletes_nothing`, `test_apply_deletes_only_expired_matches`, `test_unregistered_files_are_never_touched`, `test_path_outside_root_is_refused`.

**Commit:** `feat(lib): add artifact registry and dry-run-first prune`

---

## SPR-6 — Run-summary health check

**Files to change / create:**
- `src/lib/pipeline_runtime/health.py` — pure `check_status(summary_dict, now, max_age_s) -> list[Finding]` (failed/timed-out/skipped units, missing or stale run, unit counts).
- `scripts/check_pipeline_health.py` — thin CLI: `--status-file`, `--max-age-hours`; exit non-zero on findings; prints a digest.
- tests.

**What to implement:** read the SPR-2 status file only; no log scraping. LX-18 and the AAH alerting call this instead of each writing a parser.

**Tests:** `test_failed_unit_is_a_finding`, `test_missing_status_file_is_a_finding`, `test_stale_run_is_a_finding`, `test_clean_run_returns_no_findings`.

**Commit:** `feat(lib): add run-summary health check`
