# aws-access-cli hardening — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `PYTHON_DESIGN.md`, `docs/refactor/design-principles.md` and this
> project's own standards docs. After each task: set `SHA:` on the task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

All paths below are under `src/pipelines/aws_access_cli/` unless stated. Tests are offline: no Athena, no AWS, no network. Every refactor task must keep existing CSV output identical.

---

## AAH-1 — Run summary record and non-zero-exit alerting

**Revised 2026-11-02 (needs SPR-2):** do not write `UnitResult`, `RunSummary` or the atomic status writer here; they live in `src/lib/pipeline_runtime/` (`docs/plan/shared-pipeline-runtime/`). This
task adapts `SubReport` and `run_for_all_tenants` to build `Unit`s and call `run_units` with the in-process runner, writes the status file through `write_status`, and wires the three
`run_*_reports.py` mains. The tests below that cover the summary and atomic write move to SPR-2; keep only the AWS wiring tests (2 tenants × 2 fake reports, one raising → non-zero exit and `failed` in
the file).

**Files to change / create:**
- `schedule.py` — return a typed `UnitResult(tenant, report, period_value, status, exit_code, duration_s, error)` per unit instead of a bare int; add `RunSummary` with `exit_code` and `to_dict()`.
- Write the status file with `json` plus an atomic temp-file rename inside `schedule.py`; `src/lib/*` is not touched.
- `scripts/run_daily_reports.py`, `scripts/run_weekly_reports.py`, `scripts/run_monthly_reports.py` — write `logs/aws_access_cli_status.json` and log one summary line (`units`, `failed`,
  `duration_s`).
- `tests/test_schedule.py` — extend.

**What to implement:**

1. `run_for_all_tenants` collects a `UnitResult` per unit; the existing max-exit-code behaviour is kept as `RunSummary.exit_code`.
2. After the run, write the status file (fcid, start/end time, units list) and log `failed=N`.
3. Return `RunSummary.exit_code` from `main`, so cron sees the non-zero status.

**Tests (no network, no real external services):**
- `test_summary_lists_every_unit_with_status` — 2 tenants × 2 fake reports, one raising; the failed unit is `failed`, the rest `ok`.
- `test_exit_code_is_nonzero_when_any_unit_fails` — and zero when all pass.
- `test_status_file_written_atomically` — file parses as JSON and has the fcid.

**Commit:** `feat(aws-access-cli): add run summary and exit alerting`

---

## AAH-2 — Preflight failure isolation and mid-run SSO re-check

**Revised 2026-11-02 (needs SPR-3):** the once-per-run pre-flight, the no-traceback failure and the rate-limited single re-check are `Preflight`/`retry_if` in `src/lib/pipeline_runtime/`. This task
only injects the AWS `refresh` (over `make_auth().ensure_session(profile)`) and the `retry_if` predicate for `AthenaAuthError`; `ensure_session_once` in `common.py` is not written. Keep the three
tests as integration tests against fakes.

**Files to change / create:**
- `schedule.py` — wrap `preflight()` in try/except; on failure log with the fcid, mark every unit `skipped`, return exit 1.
- `scripts/common.py` — add `ensure_session_once(profile)` helper used by the runner when a unit raises an auth error (`AthenaAuthError`).
- `tests/test_schedule.py`, `tests/test_runtime.py` — extend.

**What to implement:**

1. A preflight exception no longer propagates as a traceback; the run ends with exit 1 and a status file (AAH-1).
2. When a unit raises `AthenaAuthError`, call the preflight once (rate-limited to once per run) and retry that unit once; a second failure marks it failed.
3. Do not retry non-auth errors.

**Tests (no network, no real external services):**
- `test_preflight_failure_returns_1_and_skips_units`.
- `test_auth_error_triggers_single_recheck_and_one_retry`.
- `test_non_auth_error_is_not_retried`.

**Commit:** `fix(aws-access-cli): isolate preflight and re-check sso`

---

## AAH-3 — Per-unit timeout and per-metric isolation

**Revised 2026-11-02 (needs SPR-2):** the unit timeout is `make_inprocess_runner(timeout_s)` in `src/lib/pipeline_runtime/`; do not add a second thread/timeout implementation to `schedule.py`. Pass
`unit_timeout_s` (default 900) through. The `adoption.py` per-metric isolation (`ReportIncompleteError`) stays here unchanged: it is AWS-specific.

**Files to change / create:**
- `schedule.py` — add `unit_timeout_s` (default 900) enforced with a worker thread and `future.result(timeout=…)`; log the timeout and mark the unit `timed_out`.
- `adoption.py` — `build_adoption_report` collects per-metric failures and raises one `ReportIncompleteError` listing them, so the caller never writes a partial date.
- `tests/test_adoption.py`, `tests/test_schedule.py` — extend.

**What to implement:**

1. A unit that exceeds the timeout is recorded `timed_out` and the loop continues. A Python thread cannot be killed, so the Athena query keeps polling until its own 300s limit; document that.
2. A failing metric no longer stops the other metrics from running and logging, but the date is not written unless all metrics succeeded.

**Tests (no network, no real external services):**
- `test_unit_exceeding_timeout_is_marked_timed_out`.
- `test_failed_metric_does_not_write_partial_date`.
- `test_all_metric_failures_are_reported_together`.

**Commit:** `feat(aws-access-cli): add unit timeout and metric isolation`

---

## AAH-4 — Empty-day sentinel for header-only CSVs

**Files to change / create:**
- `src/lib/csv_io/existing_output.py` — `csv_has_data` stays unchanged; add `csv_is_marked_empty(path)` that reads a sidecar `<file>.empty` JSON `{date, fcid, checked_at}`.
- `scripts/common.py` — `_skip_if_output_exists` also skips when the sidecar exists for a date older than `--retry-blank-days`; `run_position_cli` writes the sidecar only after a successful query that
  returned zero rows.
- `tests/test_ported_helpers.py`, `tests/lib/csv_io/` — extend.

**What to implement:**

1. A query that succeeds with zero rows writes the header-only CSV and the sidecar; a failed query writes neither.
2. Days inside the retry window are still re-queried (late data); older days are skipped.
3. `--force` ignores the sidecar.

**Tests (no network, no real external services):**
- `test_empty_result_writes_sidecar`.
- `test_failed_query_writes_no_sidecar`.
- `test_old_empty_day_is_skipped_recent_one_is_retried`.
- `test_force_ignores_sidecar`.

**Commit:** `feat(aws-access-cli): mark genuinely empty days`

---

## AAH-5 — `--force` scope across catch-up dates

**Files to change / create:**
- `scripts/run_daily_reports.py`, `scripts/run_weekly_reports.py`, `scripts/run_monthly_reports.py` — decide with the owner before coding: (a) `--force` applies to every date in the window, or (b)
  keep last-date-only and rename the help text to say so. Default proposal: (a) plus `--force-target-only` for the old behaviour.
- `tests/test_schedule.py`, `tests/test_wrappers_smoke.py` — extend.

**What to implement:**

1. `build_argv` adds `--force` according to the chosen rule; help text states it.
2. `docs/usage.md` documents the flag.

**Tests (no network, no real external services):**
- `test_force_applies_to_all_dates` (or `…_to_last_date_only`, per decision).
- `test_force_target_only_keeps_old_behaviour`.

**Commit:** `fix(aws-access-cli): define force scope for catch-up`

---

## AAH-6 — Output and log retention

**Revised 2026-11-02 (needs SPR-5):** no new prune engine. Declare this pipeline's artifacts (position CSVs, cron `.out` files, `app.log`) as `Artifact` registry rows and run them through
`scripts/prune_artifacts.py`; log rotation of `app.log` stays here if the logger config is the right place. The dry-run-default and `SCRIPTS.md` requirements are satisfied by SPR-5; this task adds the
registry module and its tests only.

**Files to change / create:**
- `scripts/aws_access_cli_retention.py` (repo-level `scripts/`, not in the package) — argparse CLI: `--output-dir`, `--logs-dir`, `--keep-days-position`, `--keep-days-logs`, `--apply` (default
  dry-run).
- `src/lib/logging/dated_logs.py` — reuse `prune_dated_logs` for dated files; add a size-based truncation helper only if none exists.
- `tests/` for the script; `SCRIPTS.md` (workspace root) — add the entry.

**What to implement:**

1. Prune `output/<T>/daily/*_shaka-1xxx-position-report.csv` older than N days (default 60). Never touch adoption, shaka-error or perpetual weekly/monthly files.
2. Rotate `logs/cron_*_v2.out` and `logs/app.log` by age or size (default: keep 30 days).
3. Dry-run prints counts and bytes it would remove.

**Tests (no network, no real external services):**
- `test_dry_run_deletes_nothing_and_reports_counts`.
- `test_apply_prunes_only_old_position_files`.
- `test_monthly_and_adoption_files_are_never_pruned`.

**Commit:** `feat(aws-access-cli): add output and log retention`

---

## AAH-7 — `ReportSpec` registry and one `run_report`

**Files to change / create:**
- `reports.py` (new) — frozen `ReportSpec(name, artifact, period_support, append_store, query_fn, write_fn)` and `REPORTS: dict[str, ReportSpec]`; a `ReportDeps` dataclass holding injected catalog,
  athena factory, reader, writer, resolver and auth.
- `scripts/common.py` — replace `run_adoption_cli`, `run_shaka_cli`, `run_position_cli` with `run_report(spec, args, deps)`; pass `RunOptions(force, retry_blank_days, skip_auth_check, tenant, table)`
  instead of the whole `argparse.Namespace`; type `resolve_range` as a `DateRange` dataclass.
- `scripts/run_*_reports.py` — build `_SUB_REPORTS` from `REPORTS` keys.
- `tests/` — update; add `tests/test_reports.py`.

**What to implement:**

1. Capture a baseline first: run daily with `--dry-run` for 2 tenants and save the output paths, plus copy two sample CSV days.
2. Move artifact names and append-store membership into `ReportSpec`; delete `_MONTHLY_APPEND_ARTIFACTS` and `adoption_metrics()`.
3. Keep the thin `run_*.py` wrappers' public `main`.
4. Re-run the baseline and diff.

**Tests (no network, no real external services):**
- `test_registry_covers_every_scheduled_report`.
- `test_run_report_uses_injected_collaborators` — fake athena and writer, asserts no real client built.
- `test_adding_a_report_needs_only_a_registry_entry`.
- Existing append and filename tests stay green unchanged.

**Commit:** `refactor(aws-access-cli): add ReportSpec registry`

---

## AAH-8 — Deduplicate date, batch and error-code helpers

**Files to change / create:**
- `dates.py` (new) — `iso_date`, `next_date`, `week_range`, `month_range`.
- `batching.py` or `src/lib/` — one `batched` and `SESSION_ID_BATCH_SIZE`; decide whether this belongs in `src/lib/` using FCT-1's shared-vs-specific test and record the decision in this task's commit
  body.
- `shaka_errors.py` — one `SHAKA_ERROR_CODES` constant used by `position_report.py` and `common.py`; remove unused `build_error_1xxx_session_ids` or wire `position_report` to it.
- `adoption.py`, `position_report.py`, `scripts/common.py` — import from the new modules; collapse the duplicated week/month block in `resolve_range` and the filename branches in
  `run_incomplete_investigation_cli`.
- `tests/` — extend.

**What to implement:**

1. Replace each duplicate with an import; no behaviour change.
2. `grep` shows a single definition of each helper afterwards.

**Tests (no network, no real external services):**
- `test_month_range_handles_february_and_december`.
- `test_batched_splits_at_boundary_and_handles_empty`.
- `test_error_codes_are_1001_to_1010`.

**Commit:** `refactor(aws-access-cli): deduplicate shared helpers`

---

## AAH-9 — Merge shaka queries and combine `unified_sessions` metrics

**Files to change / create:**
- `queries/athena/aws-access-cli_shaka_error_counts.sql` — add a second column so one query returns hhid and session distinct counts; keep the old key working until both consumers move.
- `queries/athena/aws-access-cli_adoption_combined_unified_sessions.sql` (new) — conditional `count(distinct if(...))` for the metrics that scan `unified_sessions`, one row per `session_date`.
- `adoption.py`, `shaka_errors.py`, `scripts/common.py` — consume the combined results and still emit the same column headers and order.
- `tests/test_adoption.py`, `tests/test_shaka_errors.py`, `tests/test_query_catalog_usage.py` — extend.

**What to implement:**

1. Measure first: record query count per run (baseline 163 for the daily run, 2026-11-02) and Athena bytes scanned for one tenant-day, if available from the Athena console or `get_query_execution`;
   otherwise record "not measured".
2. Implement the merged queries, run both old and new on one sample tenant-day against Athena, and diff the CSVs; they must match.
3. Keep the old queries until the diff passes; remove them in the same commit only if it does.

**Tests (no network, no real external services):**
- `test_combined_query_renders_all_expected_columns`.
- `test_merged_shaka_row_matches_two_separate_pivots` — fixture rows.
- `test_every_metric_column_header_is_preserved_in_order`.

**Commit:** `perf(aws-access-cli): merge overlapping athena queries`

---

## AAH-10 — Parallelise tenants with a bounded pool

**Revised 2026-11-02 (needs SPR-4; do after AAH-7):** the pool, deterministic ordering, failure isolation and Athena cap are `run_pool` in `src/lib/pipeline_runtime/`; do not add a
`ThreadPoolExecutor` to `schedule.py`. This task passes one group per tenant, adds `--max-workers`, builds one Athena client per tenant, and keeps the throttling warning. Its tests shrink to the AWS
wiring (one client per tenant, `--max-workers 1` equals today's serial output).

**Files to change / create:**
- `schedule.py` — run tenants (not reports within a tenant) in a `ThreadPoolExecutor(max_workers=N)`; `--max-workers` flag (default 1, so behaviour is opt-in), deterministic result order.
- `scripts/common.py` — build one Athena client per tenant and share it across that tenant's reports (removes per-report client setup).
- `tests/test_schedule.py` — extend.

**What to implement:**

1. Tenants write to separate folders, so CSV writes do not collide; confirm `MonthlyCsvStore.replace_date` locking is per file.
2. The AAH-1 summary is thread-safe (collect results, write once).
3. Keep the adapter's throttle backoff; log a warning when throttling occurs with `max_workers > 1`.
4. Do not make this the default until a real run with 4 workers shows no throttling errors in `app.log`.

**Tests (no network, no real external services):**
- `test_results_are_ordered_by_tenant_regardless_of_completion_order`.
- `test_one_tenant_failure_does_not_cancel_others`.
- `test_max_workers_one_matches_serial_behaviour`.

**Commit:** `feat(aws-access-cli): run tenants concurrently`
