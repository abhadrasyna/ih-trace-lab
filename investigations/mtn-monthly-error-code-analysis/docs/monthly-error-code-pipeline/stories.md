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
three extra columns so the leftover (`attempts_sum_check`) can be explained. Column meanings (from `queries/athena/aws-access-cli_adoption_playback_outcome.sql` and `adoption.py`, plus one verified
data check):
- Session lifecycle (user's definition): `REQUEST_VIEWING`/`PLAYING`, optionally `BUFFERING`/`PLAYING`, then `PLAY` with `DESTROY` (success), `PLAYER_ERROR` (play-stage error) or `TIMEOUT`. The
  `REQUEST_VIEWING` end reason says how the request phase ended: `PLAYING` = handed over to play, `PLAYER_ERROR` = VSF, `DESTROY` = EBVS, `OTHER` = unclassified (2 sessions in ZA September). `PLAY` is
  an `event_type`, never an `endreason`.
- VSF — `REQUEST_VIEWING` with `PLAYER_ERROR`. It has a known end reason, so it is its own bucket and is not incomplete.
- EBVS — decided: the broader definition used by the shared SQL, i.e. a session with no `PLAY` row and a `DESTROY` on any row. This includes `REQUEST_VIEWING`/`DESTROY` and also sessions whose only
  `DESTROY` is on a `BUFFERING` row. How many sessions the broader rule adds beyond `REQUEST_VIEWING`/`DESTROY` is unmeasured.
- `playing_no_end_sessions` (final name; replaces the shared pipeline's `incomplete_no_destroy_sessions`, whose name was confusing because VSF also has no `DESTROY`) — a session with no `PLAY` row, no
  `DESTROY` and no VSF, i.e. `REQUEST_VIEWING`/`PLAYING` (optionally with `BUFFERING`/`PLAYING`) and no closing `PLAY` row. Intended reading (user's understanding): playback began and the viewer
  killed the app, so no end event was reported. Verified on ZA 2026-09-15 (Athena execution `90f7deed-c31a-4500-89d6-3163afce46b9`): 28 such sessions, all `REQUEST_VIEWING`/`PLAYING` (17 with that row
  only, 11 also with `BUFFERING`/`PLAYING`), 26 mobile and 2 desktop. This supports the app-kill reading but does not prove it. One day, one OpCo.
- `play_stage_error_sessions` — a `PLAY` event with `endreason = PLAYER_ERROR`.
- `play_timeout_sessions` — a `PLAY` event with `endreason = TIMEOUT`.
- Final: VSF is its own bucket and `playing_no_end_sessions` excludes VSF, so the six outcome columns (success, VSF, EBVS, playing-no-end, play-stage error, play-timeout) are disjoint and their sum
  must equal `VOD-Playback-Attempt-Sessions` on every day. `attempts_sum_check` holds that sum; compare it with the attempts column (no separate difference column).
- Current shared SQL (`queries/athena/aws-access-cli_adoption_playback_outcome.sql`) has no VSF branch: a session's outcome is the `endreason` of its `PLAY` row when present; otherwise EBVS if a
  `DESTROY` appears anywhere in the session, else `INCOMPLETE_NO_DESTROY`. VSF sessions therefore land in `INCOMPLETE_NO_DESTROY` today. Verified on ZA 2026-09-15 (execution
  `e52b4239-7cda-49c5-a1e3-aaba08decd98`): attempts 309, success 230, VSF 27, EBVS 16, incomplete 55 (27 VSF + 28 truly incomplete), play-stage error 8, timeout 0; the six-column sum is 336 = 309
  + 27. Decided: the exclusion is a new template in this investigation (MEC-8); the shared SQL and `adoption.py` are not edited because other reports (ctap-smvod and aws_access_cli) depend on the old
    labels.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — add `--artifact adoption-gap-analysis-session`.
- `investigations/mtn-monthly-error-code-analysis/scripts/add_attempts_sum_check.py` — pure post-step that appends the `attempts_sum_check` column to a gap CSV.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py`, `tests/test_add_attempts_sum_check.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — document both.

**What to implement:**

0. Depends on MEC-8 (the new outcome template and wrapper). Do MEC-8 first. The final columns are, in order: `session_date`, `VOD-Playback-Attempt-Sessions`, `Successful-VOD-Playback-Sessions`,
   `VSF-Sessions`, `EBVS-Sessions`, `playing_no_end_sessions`, `play_stage_error_sessions`, `play_timeout_sessions`, `attempts_sum_check`.
1. Do not use the shared `GAP_SESSION_METRICS` (its incomplete column includes VSF); use the MEC-8 wrapper. The reference CSV only shows which fields exist. Reference:
   `aws-access-cli/output/ZA/daily/<yyyymm>_athena_adoption_gap_session_sample.csv` — "sample" is only that script's filename suffix; it covers a whole month. This reads `unified_<id>` tables, not the
   `_sept26` tables.
2. This artifact is not an append artifact, so run one range call per OpCo (`--start-date 2026-09-01 --end-date 2026-09-30 --period day --tenant T --output-dir ...`), not a per-date loop. Confirm
   where the range file is written (`format_range_filename`) on a `--dry-run`/first run, and document the real path in `usage.md`.
3. The ported pipeline has no `attempts_sum_check` column (the original adds it). Final: a single `attempts_sum_check` = Successful + VSF + EBVS + `playing_no_end_sessions` + play-stage error +
   play-timeout, to be compared with VOD-Playback-Attempt-Sessions; they must be equal (ZA 2026-09-15: 230 + 27 + 16 + 28 + 8 + 0 = 309). There is no second adjusted column and no difference column.
   Add the column with `add_attempts_sum_check.py` in this investigation instead of editing the shared pipeline; treat blank cells as 0. Any day where the sum differs from attempts is a finding to
   report, not to patch over.

**Tests (no network, no real external services):**
- `test_gap_artifact_runs_one_range_call_per_opco` — 4 calls, each with the month's start/end dates, using the MEC-8 wrapper and column names.
- `test_sum_check_adds_column_and_treats_blank_as_zero` — `attempts_sum_check` equals the sum of the six disjoint component columns (VSF not double-counted in incomplete).
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

---

## MEC-8 — VSF-aware playback-outcome template and gap wrapper

**Why:** the shared playback-outcome SQL has no VSF branch, so VSF sessions fall into its `INCOMPLETE_NO_DESTROY` default and the outcome columns overlap (ZA 2026-09-15: six-column sum 336 vs attempts
309). This task adds a new template used only by this investigation, so the outcome buckets are disjoint. The shared template, `adoption.py` and the other reports that depend on the old labels
(`aws-access-cli_playback_outcome.sql`, `ctap-smvod-playback-outcome.sql`, `aws-access-cli_incomplete_no_destroy_session_ids.sql`, the ctap-smvod scripts) are not edited.

**Files to change / create:**
- `queries/athena/mtn-monthly_playback_outcome_vsf.sql` — per-session outcome with the placeholders of the shared template; register per `docs/guides/query-catalog.md`.
- `investigations/mtn-monthly-error-code-analysis/scripts/run_gap_session_report.py` — thin wrapper: its own `MetricSpec` tuple using the new template for the six outcome columns, the existing
  distinct query for attempts, the shared run/report helpers from `src/pipelines/aws_access_cli`, then `add_attempts_sum_check.py` (MEC-2). `--dry-run` supported.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_gap_session_report.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register.

**What to implement:**

1. Outcome rule per session (`parent_session_id`, `timestamp_formatted`), first match wins:
   1. a `PLAY` row exists: the outcome is that row's `endreason` (`DESTROY` = success, `PLAYER_ERROR` = play-stage error, `TIMEOUT` = play timeout);
   2. else `REQUEST_VIEWING` with `PLAYER_ERROR` exists: `VSF`;
   3. else a `DESTROY` on any row: `EBVS` (the broader shared definition, kept on purpose);
   4. else `PLAYING_NO_END`.
2. Output column names: `VOD-Playback-Attempt-Sessions`, `Successful-VOD-Playback-Sessions`, `VSF-Sessions`, `EBVS-Sessions`, `playing_no_end_sessions`, `play_stage_error_sessions`,
   `play_timeout_sessions`. The household gap columns are out of scope (the household CSV, MEC-1, is unchanged).
3. Read `unified_<id>.unified_sessions`, not the `_sept26` debug tables. Resolve each tenant with `scripts/resolve_tenant.py` (by Athena id) before any Athena call. The first live run is a separate
   go-ahead from the user.
4. Open checks to report, not assume: (a) whether the template must also restrict to sessions that have a `REQUEST_VIEWING` row for the sum to equal attempts (the shared SQL does not; it matched on ZA
   2026-09-15); (b) how many sessions have both `REQUEST_VIEWING`/`PLAYER_ERROR` and a `DESTROY`, which rule 2 counts as VSF; (c) the same sum check on NG, ZM and GH.

**Tests (no network, no real external services):**
- `test_template_renders_with_database_and_dates` — the template renders with all placeholders resolved.
- `test_template_has_vsf_branch_before_ebvs` — the rendered SQL checks the `PLAY` row, then VSF, then `DESTROY`, then `PLAYING_NO_END`, in that order.
- `test_metric_specs_use_final_column_names` — the wrapper emits exactly the columns in step 2 and no `incomplete_no_destroy_sessions`.
- `test_dry_run_makes_no_athena_calls` — `--dry-run` prints the plan and calls no client.

**Commit:** `feat(mec): add VSF-aware playback-outcome template and gap wrapper`

---

## MEC-9 — September guest-session-report CSV for all OpCos

**Why:** the reference is `aws-access-cli/output/ZA/daily/202609_guest_session_report.csv` (in `~/github_copilot/`): one row per day with `session_date`, `unique_guest_session`,
`guest_login_prompt_hhid`, `guest_login_start_hhid`, `guest_login_cancel_hhid`. It shows how many guest sessions start and how many guests reach, start or cancel the login prompt. The reference only
shows which fields exist; this task regenerates it in this investigation for all four OpCos.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — add `--artifact guest-session-report`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py` — cover the new option.
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — document it.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_guest_session_report.py` (`main(argv)` → `common.run_adoption_cli`, metrics `GUEST_METRICS`, artifact `guest-session-report`); do not copy its SQL.
2. Same per-date x per-OpCo append loop as MEC-0/MEC-1 (`--date D --tenant T --output-dir investigations/mtn-monthly-error-code-analysis/output --skip-auth-check`), producing
   `output/<OPCO>/daily/2026-09_guest-session-report.csv`. Confirm the real filename on a `--dry-run`.
3. Table choice (the one difference from MEC-0/MEC-1): of the four metrics, only `unique_guest_session` reads a debug-events table (`queries/athena/aws-access-cli_unique_guest_session.sql`: distinct
   `clientid` where `split_part(clientid, ':', 2) LIKE 'GUEST.%'`, filtered on `datetime`). The pipeline's default is `<id>_ccl_debug_events` (`tenants.py`), not the September table, so the
   orchestrator must pass `--table <id>_ccl_debug_events_sept26` per OpCo (`prompt.md` "Data sources"). The other three metrics read `fact_navigation_interactions` in `unified_<id>` and ignore
   `--table`. The table name for other months is not assumed from the `sept26` suffix.
4. Count grain: distinct `clientid`, so duplicate `messageid` rows in the debug table do not inflate it (unlike MEC-3's raw event counts). The `sept26` table also holds rows from before September; the
   query's `datetime` filter bounds each day.
5. Open checks to report, not assume: (a) whether `unique_guest_session` from the `_sept26` table matches the reference CSV for ZA (reference 2026-09-01: 203, so a mismatch would mean the reference
   used the default table or a different guest rule); (b) the guest columns for NG, ZM and GH are unverified; (c) the `HHID` columns count distinct `user_id`, so they cannot be summed across days.
6. The first live Athena run is a separate go-ahead from the user; resolve each tenant with `scripts/resolve_tenant.py --system athena --tenant <athena_id>` first.

**Tests (no network, no real external services):**
- `test_guest_artifact_selects_guest_runner` — `--artifact guest-session-report` calls the guest runner with the expected `--date`/`--tenant`/`--output-dir` argv.
- `test_guest_artifact_passes_sept26_table_per_opco` — each OpCo's argv carries `--table <id>_ccl_debug_events_sept26` with that OpCo's Athena id.
- `test_guest_artifact_covers_every_date_and_opco` — a 30-day month x 4 OpCos yields 120 calls.

**Commit:** `feat(mec): add September guest-session-report to month orchestrator`

---

## MEC-10 — Guest-login funnel rates and co-movement with playback attempts

**Why:** the goal is to tell whether guest sessions are working: do guests who see the login prompt go on to start login, or cancel? A guest cannot start playback; they must log in first, so guest
activity can only raise playback attempts through logged-in sessions afterwards. This task answers the daily-aggregate part of that; MEC-11 tests the household-level link.

**Units (state first):** `unique_guest_session` counts distinct `clientid` (debug table); the three `*_hhid` columns count distinct `user_id` (navigation table). They are different units, so
`unique_guest_session` is never divided by or summed with the household columns as if comparable. The three household columns are not disjoint: on ZA 2026-09-01 prompt 83, start 66, cancel 34, so
start + cancel (100) exceeds prompt (83) because a household can start and then cancel. Report the rates separately; never present them as shares summing to 100%.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/build_guest_funnel.py` — thin script: `--month YYYY-MM` (required), `--opco` (repeatable, default all four), `--dry-run`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_build_guest_funnel.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register.

**What to implement:**

1. Depends on MEC-0, MEC-1 and MEC-9 outputs. Read `<YYYY-MM>_guest-session-report.csv`, `<YYYY-MM>_adoption-session-report.csv` and `<YYYY-MM>_adoption-report.csv` with the `src/lib/csv_io` helpers
   and join on `session_date`. Fail loudly if a file or required column is missing or the three day sets differ.
2. Per day: `guest_start_rate` = `guest_login_start_hhid` / `guest_login_prompt_hhid`, `guest_cancel_rate` = `guest_login_cancel_hhid` / `guest_login_prompt_hhid`, `guest_prompt_to_start_gap` = prompt
   − start (households that saw the prompt but did not start login), plus `guest_start_dod_pct` and the day-over-day change of `VOD-Playback-Attempt-Sessions` and `attempts-unique-hhid`. A blank or
   zero denominator gives a blank cell, not a crash or a fake zero.
3. Per OpCo, one monthly summary row: Pearson correlation of daily `guest_login_start_hhid` with `attempts-unique-hhid` and with `VOD-Playback-Attempt-Sessions`, plus the day count. Label it as
   co-movement of 30 daily points, not attribution: it cannot separate guests who log in from returning logged-in users, and guests cannot play without logging in.
4. Write `output/<OPCO>/daily/<YYYY-MM>_guest-funnel.csv`. No Athena calls.

**Tests (no network, no real external services):**
- `test_rates_computed_per_day` — known inputs give the expected start and cancel rates, and start + cancel may exceed 100% of prompt without error.
- `test_zero_denominator_gives_blank` — a zero prompt count yields a blank cell.
- `test_missing_file_column_or_day_mismatch_fails` — a missing input, column or differing day set raises a clear error.
- `test_correlation_is_reported_with_day_count` — a known series gives the expected correlation and the day count.

**Commit:** `feat(mec): add guest-login funnel and co-movement report`

---

## MEC-11 — Guest-login to playback attribution (gated on an MCP check)

**Why:** MEC-10 can only show co-movement. The attribution question is household-level: of the households that started guest login (or cancelled it), how many attempted or completed playback within 24
hours afterwards? It is not necessary to complete this task. Validate on one or two households first through the Athena MCP, and continue only if that is fruitful.

**Step 0 — gate (no files, a separate go-ahead from the user):**
1. Resolve the tenant with `python scripts/resolve_tenant.py --system athena --tenant e6auj7k7`, then use the Athena MCP (restart the CLI first; the server was repinned to `mcp` 1.30.0) for one OpCo
   and one day. Read-only.
2. In `unified_<id>.fact_navigation_interactions`, find 1-2 `user_id`s with `event_source = 'guestLoginStart'` and, separately, one with `guestLoginCancel` (columns: `user_id`, `device_id`, `uid`,
   `nav_event_time`; confirm them in `knowledge/mtn-athena-unified_e6auj7k7-tables.md`).
3. For each, look in `unified_sessions` for `REQUEST_VIEWING` rows (and `PLAY`/`DESTROY` success) with the same `user_id` within 24h after `nav_event_time`. Also check whether the guest event's
   `user_id` is the id used after login; if not, try `device_id`.
4. Record the evidence and a go or no-go in `docs/guest-login-attribution-check.md`. Go only if at least one sampled household shows start followed by an attempt under a matchable id. On no-go, stop:
   MEC-11 closes with the finding and no further files.

**Files to change / create (only on a go):**
- `queries/athena/mtn-monthly_guest_login_attribution.sql` — per day, using the id proven in step 0: `guest_start_hhid`, of which `attempted_24h` and `succeeded_24h`; the same for cancel. Register in
  `queries/athena/index.md` per `docs/guides/query-catalog.md`.
- `investigations/mtn-monthly-error-code-analysis/scripts/run_guest_login_attribution.py` — thin orchestrator: `--month YYYY-MM`, `--opco` (repeatable, default all four), `--dry-run`; renders via
  `QueryCatalog`, runs via `src/lib/athena`, writes `output/<OPCO>/daily/<YYYY-MM>_guest-login-attribution.csv`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_guest_login_attribution.py`, plus `docs/usage.md` and `SCRIPTS.md`.

**What to implement (only on a go):**

1. Window is 24 hours after the household's first `guestLoginStart` (or `guestLoginCancel`) event that day. Attempt = a `REQUEST_VIEWING` session; success = a `PLAY` row with `endreason = 'DESTROY'`.
2. Report attribution as association, not cause: a household that starts login and then plays was already a viewer who needed to log in; the comparison that matters is the start group against the
   cancel group. No baseline of non-guest households is claimed.
3. Household ids are customer identifiers: do not commit raw `user_id` outputs without the user's go-ahead. The CSV holds counts only.
4. The first live full-month run is a separate go-ahead from the user.

**Tests (no network, no real external services):** `test_query_renders_for_month` (all placeholders resolve), `test_bad_month_fails`, `test_dry_run_makes_no_athena_calls`.

**Commit:** `docs(mec): record guest-login attribution check` for the gate; `feat(mec): add guest-login attribution report` only on a go.
