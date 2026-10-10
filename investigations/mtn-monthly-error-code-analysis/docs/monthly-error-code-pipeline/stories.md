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

**Why this CSV exists:** in the session report, `VOD-Playback-Attempt-Sessions` does not equal Successful + VSF + EBVS, so there is an unknown drop-off. The gap CSV attributes those sessions with
three extra columns so the leftover (`attempts_sum_check`) can be explained. Column meanings (from `queries/athena/aws-access-cli_adoption_playback_outcome.sql` and `adoption.py`; the first is the
user's operational understanding, the rest are read from the SQL):
- `incomplete_no_destroy_sessions` — playback started (a `PLAY` event was received) but no closing `DESTROY` was reported, typically a viewer who kills the app or session after a few minutes. It is
  mostly a missing end event, not a playback failure; present it separately from the failure buckets.
- `play_stage_error_sessions` — a `PLAY` event with `endreason = PLAYER_ERROR`.
- `play_timeout_sessions` — a `PLAY` event with `endreason = TIMEOUT`.
- Outcome rule: a session's outcome is the `endreason` of its `PLAY` row when present; otherwise EBVS if a `DESTROY` appears anywhere in the session, else `INCOMPLETE_NO_DESTROY`.
- Unverified: whether VSF (`REQUEST_VIEWING` with `PLAYER_ERROR`) overlaps `incomplete_no_destroy`, which would make the six-column sum exceed attempts. Compare against the reference CSV's
  `attempts_sum_check` before treating the sum as exact.

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

---

## MEC-5 — Verify one playback outcome per session

**Why:** `queries/athena/aws-access-cli_adoption_playback_outcome.sql` groups by `parent_session_id` plus `timestamp_formatted` (and `user_id` for households). If `timestamp_formatted` ever differs
between rows of one session, a session lands in several outcome buckets and the buckets no longer sum to attempts. A manual check (ZA, 2026-09-15, Athena execution
`21c7b5b1-241b-4037-8e71-af35ac75df9f`) found 309 attempts = 309 sessions = 309 bucket total, 0 multi-outcome sessions, 1 group per session, so the risk did not materialise that day. This task makes
the check repeatable for the whole month and all four OpCos. Run order: before MEC-2 is signed off. It does not change the shared query.

**Files to change / create:**
- `queries/athena/mtn-monthly_playback_outcome_uniqueness.sql` — per-day `attempts`, `sessions_total`, `sessions_multi_outcome`, `sum_of_bucket_counts` using the same outcome logic as the shared
  query; register per `docs/guides/query-catalog.md`.
- `investigations/mtn-monthly-error-code-analysis/scripts/verify_playback_outcome_uniqueness.py` — thin orchestrator: `--month YYYY-MM` (required), `--opco` (repeatable, default all four),
  `--dry-run`; resolves tenants with the existing tenant helpers, renders via `QueryCatalog`, runs via the shared `src/lib/athena` client, writes
  `output/<OPCO>/daily/<YYYY-MM>_playback-outcome-uniqueness-check.csv`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_verify_playback_outcome_uniqueness.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register the script.

**What to implement:**

1. A pure `evaluate_uniqueness(rows)` that raises a clear error when any day has `sessions_multi_outcome > 0` or `sum_of_bucket_counts != attempts`; `main()` exits non-zero on failure and never writes
   a silently wrong result.
2. Reuse existing code; do not copy the shared playback-outcome SQL beyond the CTE needed for the check.
3. The first live Athena run is a separate go-ahead from the user; resolve each tenant with `scripts/resolve_tenant.py` first.

**Tests (no network, no real external services):**
- `test_clean_rows_pass` — all days with zero multi-outcome sessions and matching sums pass.
- `test_multi_outcome_day_fails` — a day with `sessions_multi_outcome > 0` raises.
- `test_bucket_sum_mismatch_fails` — a day where the bucket sum differs from attempts raises.
- `test_dry_run_makes_no_athena_calls` — `--dry-run` prints the plan and calls no client.

**Commit:** `feat(mec): add playback-outcome uniqueness check`

---

## MEC-6 — Household concentration ratios from the session and household CSVs

**Why:** the household adoption CSV exists to cross-check the session CSV: if VSF/EBVS sessions greatly exceed the households behind them, a small group of households is driving the failures. Distinct
counts alone do not show that; the per-day ratios do. `unique-hh-no-vsf` is not used because the VSF household set is a subset of the attempted set, so it always equals `attempts-unique-hhid −
vsf-unique-hhid`.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/build_household_concentration.py` — thin script: `--month YYYY-MM` (required), `--opco` (repeatable, default all four), `--dry-run`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_build_household_concentration.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register.

**What to implement:**

1. Depends on MEC-0 and MEC-1 outputs. Read `output/<OPCO>/daily/<YYYY-MM>_adoption-session-report.csv` and `<YYYY-MM>_adoption-report.csv` with the `src/lib/csv_io` helpers and join on
   `session_date`.
2. Pure functions compute per day: `attempts_sessions_per_hh`, `success_sessions_per_hh`, `vsf_sessions_per_hh`, `ebvs_sessions_per_hh` (session column divided by the matching household column), plus
   `vsf_hh_pct` and `ebvs_hh_pct` (affected households divided by `attempts-unique-hhid`). Blank or zero denominators give a blank cell, not a crash or a fake zero.
3. Fail loudly when an input CSV or a required column is missing, or when the two CSVs do not cover the same days.
4. Write `output/<OPCO>/daily/<YYYY-MM>_household-concentration.csv`. No Athena calls.

**Tests (no network, no real external services):**
- `test_ratios_computed_per_day` — known inputs give the expected ratios and percentages.
- `test_zero_denominator_gives_blank` — a zero household count yields a blank cell.
- `test_missing_column_or_day_mismatch_fails` — a missing column or differing day sets raises a clear error.

**Commit:** `feat(mec): add household concentration ratios`

---

## MEC-7 — Top-N households by VSF/EBVS sessions

**Why:** MEC-6 shows whether failures look concentrated; this task names the households. It is a monthly roll-up, so it also shows whether the same households fail across many days.

**Files to change / create:**
- `queries/athena/mtn-monthly_top_households_by_failure.sql` — per `user_id` for the month: `attempt_sessions`, `vsf_sessions`, `ebvs_sessions`, ordered by `vsf_sessions` then `ebvs_sessions`, limited
  to `{{top_n}}`; register per `docs/guides/query-catalog.md`.
- `investigations/mtn-monthly-error-code-analysis/scripts/run_top_failure_households.py` — thin orchestrator: `--month YYYY-MM`, `--opco` (repeatable, default all four), `--top-n` (default 20),
  `--dry-run`; resolves tenants with the existing tenant helpers, renders via `QueryCatalog`, runs via `src/lib/athena`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_top_failure_households.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register.

**What to implement:**

1. Reuse the shared outcome definitions: VSF is `event_type = 'REQUEST_VIEWING' AND endreason = 'PLAYER_ERROR'`; EBVS follows the shared playback-outcome logic. Count distinct `parent_session_id` per
   household over the whole month in `unified_<id>.unified_sessions`, not the `_sept26` debug tables.
2. Add a share column per household: its `vsf_sessions` and `ebvs_sessions` as a percentage of the OpCo's month total, plus the cumulative share of the top N.
3. Write `output/<OPCO>/daily/<YYYY-MM>_top-vsf-households.csv`. Household ids are customer identifiers: `output/` is not git-ignored, so stage only files you deliberately approve and do not commit
   raw `user_id` outputs without the user's go-ahead.
4. The first live Athena run is a separate go-ahead from the user; resolve each tenant with `scripts/resolve_tenant.py` first. Run after MEC-5 so the per-session outcome is known to be unique.

**Tests (no network, no real external services):**
- `test_query_renders_for_month_and_top_n` — the template renders with database, dates and `top_n`.
- `test_bad_month_or_top_n_fails` — an invalid month or a non-positive `top_n` raises a clear error.
- `test_shares_and_cumulative_share` — known rows give the expected percentages and cumulative share.
- `test_dry_run_makes_no_athena_calls` — `--dry-run` prints the plan and calls no client.

**Commit:** `feat(mec): add top failure households report`
