# Monthly error code pipeline — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to the backlog/session-log file.

All scripts are thin: pure logic functions plus a `main()` with `argparse`, `init_logging()`, and shared code from `src/lib/` (Athena adapter, monthly CSV store, tenant registry). Before writing any
script, check `SCRIPTS.md` and the FCT-6 registry for an existing equivalent. Every output is generated for all four OpCos (ZA, NG, ZM, GH); a CSV pasted as a reference only shows which fields exist,
so find the script that generates it and reuse it for the month under analysis.

---

## MEC-0 — September adoption-session-report CSV for all OpCos

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — thin month orchestrator (shared by MEC-0, MEC-1 and MEC-2).
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — add the entry and the first run-order row.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_adoption_session_report.py` (`main(argv)` → `common.run_adoption_cli`, metrics `SESSION_METRICS`); do not copy its SQL. This report reads
   `unified_<id>.unified_sessions`, not the `_ccl_debug_events_sept26` tables.
2. Only a single `--date` run upserts into the month file via `MonthlyCsvStore` (a `--start-date/--end-date` range does not), so for this artifact the orchestrator loops every date in the month and
   every OpCo, calling `main(["--date", D, "--tenant", T, "--output-dir", "investigations/mtn-monthly-error-code-analysis/output", "--skip-auth-check"])`. Run SSO once up front; isolate
   per-date/per-OpCo failures and exit non-zero if any failed. Result: `output/<OPCO>/daily/2026-09_adoption-session-report.csv` (the output dir is resolved against the repo root).
3. Args: `--month YYYY-MM` (required), `--artifact` (`adoption-session-report` default; MEC-1 and MEC-2 add the others), `--opco` (repeatable, default all four), `--force`, `--dry-run` (print the
   plan, run nothing).
4. Decided: South Africa is `ZA` in this investigation's folders and CLI (matching `src/pipelines/aws_access_cli/tenants.py` and the existing `output/ZA/daily/` files), although `config/tenants.yaml`
   calls it `SA`. Document the mapping in `usage.md`.
5. The data must have settled: ZA session counts were still rising two days after the first run (7 Oct vs 9 Oct), so September (closed) is safe; for a current month, wait 2-3 days after month end.

**Tests (no network, no real external services):**
- `test_plan_covers_every_date_and_opco` — a 30-day month x 4 OpCos yields 120 calls, with the expected `--date`/`--tenant`/`--output-dir` argv.
- `test_failure_is_isolated_and_exit_nonzero` — one failing call does not stop the rest, and the exit code is non-zero.
- `test_bad_month_fails` — an invalid month raises a clear error.

**Commit:** `feat(mec): add September adoption-session-report orchestrator`

---

## MEC-1 — September adoption-report (household) CSV for all OpCos

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — add `--artifact adoption-report`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py` — cover the new option.
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — document it.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_adoption_report.py` (`HOUSEHOLD_METRICS`: Home-Screen-UnqHHID, attempts-unique-hhid, unique-hh-no-vsf, successful_vod_playback_hhid, vsf_unique_hhid,
   ebvs_unique_hhid). This is the counterpart of `aws-access-cli/output/ZA/daily/<yyyymm>_athena_adoption.csv`; here the file is `2026-09_adoption-report.csv`. It reads `unified_<id>` tables
   (`fact_navigation_interactions`, `unified_sessions`), not the `_ccl_debug_events_sept26` tables.
2. Same per-date x per-OpCo loop as MEC-0 (an append artifact), with `--output-dir investigations/mtn-monthly-error-code-analysis/output`.

**Tests (no network, no real external services):**
- `test_artifact_selects_household_runner` — `--artifact adoption-report` calls the household runner with the expected argv.
- `test_unknown_artifact_fails` — an unsupported artifact exits with a clear message.

**Commit:** `feat(mec): add September adoption-report to month orchestrator`

---

## MEC-2 — September adoption-gap-analysis-session CSV for all OpCos

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — add `--artifact adoption-gap-analysis-session`.
- `investigations/mtn-monthly-error-code-analysis/scripts/add_attempts_sum_check.py` — pure post-step that appends the `attempts_sum_check` column to a gap CSV.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py`, `tests/test_add_attempts_sum_check.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — document both.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_adoption_gap_analysis_session_report.py` (`GAP_SESSION_METRICS`: the four session columns plus incomplete_no_destroy_sessions,
   play_stage_error_sessions, play_timeout_sessions). Reference: `aws-access-cli/output/ZA/daily/<yyyymm>_athena_adoption_gap_session_sample.csv` — "sample" is only that script's filename suffix; it
   covers a whole month. This reads `unified_<id>` tables, not the `_sept26` tables.
2. This artifact is not an append artifact, so run one range call per OpCo (`--start-date 2026-09-01 --end-date 2026-09-30 --period day --tenant T --output-dir ...`), not a per-date loop. Confirm
   where the range file is written (`format_range_filename`) on a `--dry-run`/first run, and document the real path in `usage.md`.
3. The ported pipeline has no `attempts_sum_check` column (the original adds it: Successful + VSF + EBVS + the three gap columns, compared with VOD-Playback-Attempt-Sessions). Add it with
   `add_attempts_sum_check.py` in this investigation instead of editing the shared pipeline; treat blank cells as 0.

**Tests (no network, no real external services):**
- `test_gap_artifact_runs_one_range_call_per_opco` — 4 calls, each with the month's start/end dates.
- `test_sum_check_adds_column_and_treats_blank_as_zero` — the column equals the sum of the six component columns.
- `test_sum_check_missing_column_fails` — a CSV without a required component column raises a clear error.

**Commit:** `feat(mec): add September adoption-gap-analysis-session report`

---

## MEC-3 — Define error-code source and count grain; add catalog query

**Files to change / create:**
- `queries/athena/mtn-monthly-error-code-counts.sql` — month-parameterized error-code count query.
- `investigations/mtn-monthly-error-code-analysis/docs/error-code-source.md` — chosen table, field, count grain, OpCo database naming.
- catalog entry per `docs/guides/query-catalog.md`.

**What to implement:**

1. The September 2026 source tables are in `prompt.md` "Data sources" (`<athena_tenant_id>_ccl_debug_events_sept26` inside `unified_<id>`). Verified on ZA/ZM: `eventid = 'PLAYER_ERROR'` and
   `eventdata.errorcode`; raw events are about 2x distinct `messageid`, and the `sept26` table also holds rows from before September, so filter `datetime` to 2026-09-01..2026-10-01. Wait for the
   user's dedup/count-grain decision before writing the SQL.
2. Adapt the closest prior art (`ctap-smvod-error-eventdata.sql` first, `aws-access-cli_shaka_error_counts.sql` second) with a whole-month predicate so counts are not double-counted across days; reuse
   `ctap-smvod`'s `render_query` and `resolve_tenant_context(code, table_suffix="sept26")` instead of new plumbing.
3. Document the decisions in `error-code-source.md`.

**Tests (no network, no real external services):**
- `test_query_renders_for_month` — the catalog template renders with OpCo and month parameters.
- `test_query_rejects_bad_month` — an invalid month raises a clear error.

**Commit:** `feat(mec): add monthly error-code catalog query`

---

## MEC-4 — Finalize runbook, usage.md, SCRIPTS.md

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — fill the run-order table and one entry per script.
- `SCRIPTS.md` — register every new script.
- `CONTEXT.md` — update "What Exists".

**What to implement:**

1. Replace the "(TBD)" rows in `usage.md` with the real scripts, args, inputs, outputs and examples.
2. Add the first dated findings doc, `docs/YYYY-MM-all-findings.md`, from a real run.

**Tests:** none (docs only); verify the documented commands run.

**Commit:** `docs(mec): finalize monthly error-code runbook`
