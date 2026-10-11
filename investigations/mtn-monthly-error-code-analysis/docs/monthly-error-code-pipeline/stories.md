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
three extra columns so the leftover (`attempts_sum_check`) can be explained.

**Reference-review findings (ZA, September, fresh Athena counts taken 2026-10-11 after the data settled; counts only):**
- The leftover is not unexplained and is mostly not failure: 582 of 5,029 attempts (11.6%) = 319 plays with no end record + 161 `PLAY`/`PLAYER_ERROR` + 102 `PLAY`/`TIMEOUT`. Conviva's identity
  Attempts = Plays + VSF + EBVS holds: Plays (`REQUEST_VIEWING`/`PLAYING`) 3,967 (78.9%) + VSF 765 (15.2%) + EBVS (`REQUEST_VIEWING`/`DESTROY`) 296 (5.9%) + other 1 closes to attempts on 29 of 30 days
  (09-18 is off by 1 session). This session-grain funnel is the headline; the six columns below are its breakdown of Plays and the failure buckets. MEC-8 carries the rule.
- Blank cells in the reference mean zero (`play_timeout_sessions`, `play_stage_error_sessions`, `EBVS-Sessions` on thin days); the output writes explicit zeros.
- The reference `202609_athena_adoption_gap_session_sample.csv` is a partial, stale sample (generated 2026-09-24, 24 rows, the 09-24 row is a half day with 6 attempts) and is not a valid September
  CSV. Its `attempts_sum_check` exceeds attempts by 1 on 09-04, 09-06, 09-18, 09-20 and 09-24: the six columns are not yet proven disjoint (MEC-5 tests it).
- Mid-month shift to confirm (MEC-20): plays with no end record fall from about 12-31 per day to 1-3 on 09-21..23 while `play_timeout_sessions` rises to 13/9/9, and no-end is near 0-1% on 09-26 and
  09-27. This looks like a change in how unfinished sessions are closed, not viewer behaviour; any trend must combine no-end and timeout until MEC-20 settles it.

Column meanings (from `queries/athena/aws-access-cli_adoption_playback_outcome.sql` and `adoption.py`, plus one verified data check):
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
4. Extra checks added by the reference review (ZA first measurements in brackets; each is reported per day and OpCo, not assumed):
   - VSF never also plays: sessions with `REQUEST_VIEWING`/`PLAYER_ERROR` and any `PLAY` row (ZA September: 0 of 765). This is Conviva's rule that a session which errored and then played is not VSF.
   - `PLAY` sessions without a `REQUEST_VIEWING`/`PLAYING` row (ZA September: 6), which decides how Plays is defined (MEC-8).
   - Sessions carrying two `PLAY` end reasons or two `REQUEST_VIEWING` end reasons (ZA 09-18: 289 summed by end reason vs 288 distinct `PLAY` sessions; the reference sample's `attempts_sum_check`
     exceeded attempts by 1 on five days). These are the double-counts that break disjointness.
   - Funnel closure: attempts = Plays + VSF + EBVS + other per day (ZA September: closes on 29 of 30 days, 09-18 off by 1).

**Tests (no network, no real external services):**
- `test_clean_rows_pass` — all days with zero multi-outcome sessions and matching sums pass.
- `test_vsf_with_play_row_fails` — a day with a session in both VSF and `PLAY` raises.
- `test_funnel_closure_mismatch_reported` — a day where Plays + VSF + EBVS + other differs from attempts is reported with the day and the difference.
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
   `play_timeout_sessions`, plus the Conviva-aligned columns `Plays-Sessions` (see 5) and `other_start_sessions`. The household gap columns are out of scope (the household CSV, MEC-1, is unchanged).
   Cells are explicit zeros, never blank.
5. Conviva-aligned funnel (reference review, `https://docs.conviva.ai/sei/video/metric-dictionary/`; an analogy for naming and denominators, not a spec): Attempts = Plays + VSF + EBVS + other, where
   Plays = sessions that started playing (`REQUEST_VIEWING`/`PLAYING`, plus any `PLAY` session without that row so none is lost; ZA September has 6 such sessions) and `other_start_sessions` =
   `REQUEST_VIEWING`/`OTHER`. Plays split into `Successful-VOD-Playback-Sessions` + `play_stage_error_sessions` + `play_timeout_sessions` + `playing_no_end_sessions`. ZA September measurement: 3,967
   plays = 3,648 `PLAY` sessions + 319 no-end; funnel closes on 29 of 30 days.
6. Rates always state their denominator: VSF and EBVS and Plays per 100 attempts (ZA September: 15.2, 5.9, 78.9); the play-stage error rate (the "VPF-proxy") per 100 ended plays, where ended plays =
   `PLAY` sessions (`DESTROY` + `PLAYER_ERROR` + `TIMEOUT`), not per attempt (ZA September: 161 of 3,649 = 4.4%, versus 3.2% if wrongly divided by attempts). Name it VPF-proxy until the first-frame
   and buffer-length conditions of Conviva's VPF are checked; `TIMEOUT` is an ended-play outcome, not a failure. VSF, EBVS and ended plays follow Conviva's definitions closely; the EBVS rule is the
   broad shared one here, so its difference from `REQUEST_VIEWING`/`DESTROY` (296 on fresh ZA data) is measured in MEC-16.
3. Read `unified_<id>.unified_sessions`, not the `_sept26` debug tables. Resolve each tenant with `scripts/resolve_tenant.py` (by Athena id) before any Athena call. The first live run is a separate
   go-ahead from the user.
4. Open checks to report, not assume: (a) whether the template must also restrict to sessions that have a `REQUEST_VIEWING` row for the sum to equal attempts (the shared SQL does not; it matched on ZA
   2026-09-15); (b) how many sessions have both `REQUEST_VIEWING`/`PLAYER_ERROR` and a `DESTROY`, which rule 2 counts as VSF; (c) the same sum check on NG, ZM and GH.

**Tests (no network, no real external services):**
- `test_template_renders_with_database_and_dates` — the template renders with all placeholders resolved.
- `test_template_has_vsf_branch_before_ebvs` — the rendered SQL checks the `PLAY` row, then VSF, then `DESTROY`, then `PLAYING_NO_END`, in that order.
- `test_metric_specs_use_final_column_names` — the wrapper emits exactly the columns in step 2 and no `incomplete_no_destroy_sessions`.
- `test_funnel_identity_holds_on_fixture` — Plays + VSF + EBVS + other equals attempts on a fixed in-memory sample, and a sample with a double-counted session fails loudly.
- `test_vpf_proxy_uses_ended_plays_denominator` — the rate helper divides play-stage errors by ended plays, not attempts.
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

## MEC-10 — Guest-login to playback link: MCP validation (run first)

**Why:** the goal is to tell whether guest sessions are working: do guests who see the login prompt go on to start login, or cancel, and can any rise in playback attempts be attributed to them? A
guest cannot start playback; they must log in first, so guest activity can only raise attempts through logged-in sessions afterwards. Whether that link is even observable in the data is unknown, so
this task checks it before any of the guest analysis is built. It needs no CSV, so it runs first, before MEC-9, MEC-11 and MEC-12. It is a docs-only task; completing the downstream attribution is
optional.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/docs/guest-login-attribution-check.md` — the evidence and the go or no-go.

**What to implement (a separate go-ahead from the user for the Athena MCP calls):**
1. Resolve the tenant with `python scripts/resolve_tenant.py --system athena --tenant e6auj7k7`, then use the Athena MCP (restart the CLI first; the server was repinned to `mcp` 1.30.0) for one OpCo
   and one day. Read-only.
2. In `unified_<id>.fact_navigation_interactions`, find 1-2 `user_id`s with `event_source = 'guestLoginStart'` and one with `guestLoginCancel` (columns: `user_id`, `device_id`, `uid`,
   `nav_event_time`; confirm them in `knowledge/mtn-athena-unified_e6auj7k7-tables.md`).
3. For each, look in `unified_sessions` for `REQUEST_VIEWING` rows (and `PLAY`/`DESTROY` success) with the same `user_id` within 24h after `nav_event_time`. Also check whether the guest event's
   `user_id` is the id used after login; if not, try `device_id`.
4. Record the evidence and a go or no-go. Go only if at least one sampled household shows start followed by an attempt under a matchable id. On no-go, MEC-12 closes with the finding and MEC-11 still
   runs but labels its correlation as the only available signal.

**Commit:** `docs(mec): record guest-login attribution check`

---

## MEC-11 — Guest-login funnel rates and co-movement with playback attempts

**Why:** this answers the daily-aggregate part of the goal in MEC-10: whether more households fall in the start or the cancel column, and whether guest activity moves with playback attempts. MEC-12
tests the household-level link, if MEC-10 found one.

**Units (state first):** `unique_guest_session` counts distinct `clientid` (debug table); the three `*_hhid` columns count distinct `user_id` (navigation table). They are different units, so
`unique_guest_session` is never divided by or summed with the household columns as if comparable. The three household columns are not disjoint: on ZA 2026-09-01 prompt 83, start 66, cancel 34, so
start + cancel (100) exceeds prompt (83) because a household can start and then cancel. Report the rates separately; never present them as shares summing to 100%.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/build_guest_funnel.py` — thin script: `--month YYYY-MM` (required), `--opco` (repeatable, default all four), `--dry-run`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_build_guest_funnel.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` and `SCRIPTS.md` — document and register.

**What to implement:**

1. Depends on MEC-0, MEC-1 and MEC-9 outputs; MEC-10's go or no-go is quoted in the summary. Read `<YYYY-MM>_guest-session-report.csv`, `<YYYY-MM>_adoption-session-report.csv` and
   `<YYYY-MM>_adoption-report.csv` with the `src/lib/csv_io` helpers and join on `session_date`. Fail loudly if a file or required column is missing or the three day sets differ.
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

## MEC-12 — Guest-login to playback attribution (only on a MEC-10 go)

**Why:** MEC-11 can only show co-movement. The attribution question is household-level: of the households that started guest login (or cancelled it), how many attempted or completed playback within 24
hours afterwards? It is not necessary to complete this task: build it only if MEC-10 recorded a go, using the id MEC-10 proved matchable.

**Files to change / create:**
- `queries/athena/mtn-monthly_guest_login_attribution.sql` — per day, using the id proven in step 0: `guest_start_hhid`, of which `attempted_24h` and `succeeded_24h`; the same for cancel. Register in
  `queries/athena/index.md` per `docs/guides/query-catalog.md`.
- `investigations/mtn-monthly-error-code-analysis/scripts/run_guest_login_attribution.py` — thin orchestrator: `--month YYYY-MM`, `--opco` (repeatable, default all four), `--dry-run`; renders via
  `QueryCatalog`, runs via `src/lib/athena`, writes `output/<OPCO>/daily/<YYYY-MM>_guest-login-attribution.csv`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_guest_login_attribution.py`, plus `docs/usage.md` and `SCRIPTS.md`.

**What to implement:**

1. Window is 24 hours after the household's first `guestLoginStart` (or `guestLoginCancel`) event that day. Attempt = a `REQUEST_VIEWING` session; success = a `PLAY` row with `endreason = 'DESTROY'`.
2. Report attribution as association, not cause: a household that starts login and then plays was already a viewer who needed to log in; the comparison that matters is the start group against the
   cancel group. No baseline of non-guest households is claimed.
3. Household ids are customer identifiers: do not commit raw `user_id` outputs without the user's go-ahead. The CSV holds counts only.
4. The first live full-month run is a separate go-ahead from the user.

**Tests (no network, no real external services):** `test_query_renders_for_month` (all placeholders resolve), `test_bad_month_fails`, `test_dry_run_makes_no_athena_calls`.

**Commit:** `feat(mec): add guest-login attribution report`

---

## MEC-13 — September shaka-error-session CSV for all OpCos

**Why:** the reference is `aws-access-cli/output/ZA/daily/202609_shaka_error_sessions.csv` (in `~/github_copilot/`): one row per day, `session_date` plus one column per Shaka `PLAYER_ERROR` code
(`1001, 1002, 1003, 3014, 3015, 3016, 4032, 6001, 6002, 6006, 6007, 6012, 7000, E31012`, and `1006` appended late). Each cell is the number of distinct sessions that carried that code that day. The
reference only shows which fields exist; this task regenerates it in this investigation for all four OpCos. Sibling references (`202609_shaka_error_hhid.csv`,
`202609_shaka_1xxx_position_report_*.csv`) are out of scope: the hhid artifact is a possible follow-up task.

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_reports.py` — add `--artifact shaka-error-session`.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_reports.py` — cover the new option.
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — document it.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_shaka_error_session_report.py` (`main(argv)` → `common.run_shaka_cli(artifact='shaka-error-session', by='session')`, logic in `shaka_errors.py`, SQL
   `queries/athena/aws-access-cli_shaka_error_counts.sql`); do not copy its SQL. It counts `COUNT(DISTINCT json_extract_scalar(eventdata, '$.sessionid'))` per `$.errorcode` where `eventid =
   'PLAYER_ERROR'`, from the debug events table (not `unified_sessions`), with `datetime >= D 00:00Z AND < D+1 00:00Z`.
2. Same per-date x per-OpCo append loop as MEC-0/MEC-1/MEC-9 (`--date D --tenant T --output-dir investigations/mtn-monthly-error-code-analysis/output --skip-auth-check`), producing
   `output/<OPCO>/daily/2026-09_shaka-error-sessions.csv`. Confirm the real filename on a `--dry-run` (the reference name is `<yyyymm>_shaka_error_sessions.csv`).
3. Table: the orchestrator must pass `--table <id>_ccl_debug_events_sept26` per OpCo (`prompt.md` "Data sources"). The pipeline default is `<id>_ccl_debug_events`, which the user states holds only
   October data once the month rolls over (the table resets on the last day of the month). The `_sept26` table also holds pre-September rows; the `datetime` window bounds each day.
4. The ZA reference was generated from the default table (user-confirmed), not `_sept26`. This explains, as a stated cause to verify, why the reference shows 2026-09-30 as all zeros: the zero is a
   zero-fill (`pivot_error_counts` writes `0` for every column when the query returns no rows), not a measured zero. Do not treat that day as zero errors in any report built from the reference.
5. Column rules: codes outside `KNOWN_ERROR_CODES` are appended as new columns, so `1006` appears late; in the reference it is blank for 2026-09-01..21 and `0` from 2026-09-23. Blank means "column not
   yet discovered when that row was written", not a measured zero, until a month-wide run proves otherwise. A session can carry several codes, so the per-code columns must never be summed to "sessions
   with an error"; a session-with-any-error figure needs its own `COUNT(DISTINCT sessionid)` query.
6. Open checks, each an Athena run needing the user's go-ahead (report results, do not assume): (a) session id grain: per day, `COUNT(*)`, `COUNT(DISTINCT messageid)` and `COUNT(DISTINCT $.sessionid)`
   for `PLAYER_ERROR`; and whether `$.sessionid` equals `parent_session_id` in `unified_<id>.unified_sessions` for the same day. (b) 2026-09-30: `MIN/MAX(datetime)` and per-day row counts on both
   `<id>_ccl_debug_events` and `<id>_ccl_debug_events_sept26`, to separate a real zero from a table reset, lag or cutoff. (c) reference vs `_sept26` for ZA, per day and code: report differences, do
   not call them errors. Also the first date `1006` appears on each table. (d) the NG, ZM and GH outputs are unverified. (e) VSF relation: the MEC-8 `VSF-Sessions` (`REQUEST_VIEWING`/`PLAYER_ERROR`)
   against distinct `PLAYER_ERROR` sessions here, per OpCo-day: the share of VSF sessions whose id appears in the error table, and the reverse. Propose-and-measure only; no equality is assumed.
7. Relation to MEC-3 (decided: separate, cross-referenced): MEC-13 reuses the existing per-day, distinct-session, wide-pivot generator; MEC-3 is a whole-month catalog query whose count grain (raw
   events vs dedup) is still pending. They do not share a query. Check (a) is the measured input MEC-3's dedup decision can use.
8. The first live Athena run is a separate go-ahead from the user; resolve each tenant with `scripts/resolve_tenant.py --system athena --tenant <athena_id>` first (pass the id, not `ZA`). `output/` is
   not git-ignored and these files hold counts only, but do not commit them without the user's approval.

**Measured findings (ZA only, 2026-09-04/15/18, `_sept26` table, read-only Athena; session key = `COUNT(DISTINCT $.sessionid)` vs `COUNT(DISTINCT parent_session_id)`, the only session key in
`unified_sessions`):**
- Session grain: raw `PLAYER_ERROR` rows are 27/69/200, distinct `messageid` 13/36/146, distinct sessions 12/36/145. Raw rows over-count (not a fixed 2x); distinct session is the safe grain.
- The per-code column sum in the ZA reference is 12/36/146 against 12/36/145 distinct `_sept26` sessions: equal on 09-04 and 09-15, one session carrying two codes on 09-18. On these days the reference
  and `_sept26` agree.
- VSF (`REQUEST_VIEWING`/`PLAYER_ERROR`: 5/27/131) is a subset of the Shaka error sessions (every VSF session has an error event), but the Shaka count is higher, so do not use it as a VSF count.
- All `unified_sessions` sessions with any `PLAYER_ERROR` end reason (any `event_type`: 11/35/142, split `PLAY` 6/8/11 and `REQUEST_VIEWING` 5/27/131) appear in the debug table; the debug table has
  1/1/3 more. Of those 5, 4 are in `unified_sessions` with another end reason (`REQUEST_VIEWING`/`PLAYING`, `BUFFERING`/`PLAYING`, `REQUEST_VIEWING`/`DESTROY`) and 1 has no `unified_sessions` row.
  That `PLAYING` rows mean a mid-session error is an interpretation, not proven.
- Not yet measured: 09-30 and the table boundary, the 1006 blank, NG/ZM/GH, and any other day. These feed MEC-14.
- Table correction (ZA, Athena 2026-10-11): `e6auj7k7_ccl_debug_events` is not October-only; it spans 2026-08-25 17:52Z to 2026-10-11 and still contains September. `_sept26` spans 2026-08-25 04:16Z to
  2026-09-30 23:59:26Z. Use `_sept26` for September because it is frozen; whether the two tables hold identical September rows is only confirmed for 09-04/15/18 (check (c)).
- Per-code columns are not sessions: on ZA 09-04/15/18 the VSF sessions (163) carry 164 per-code sessions and the class-2 play-stage sessions (25) carry 26.

**Analysis ideas (from the CSV):**

| Idea | Needs Athena? |
|---|---|
| Daily trend per code, small multiples per OpCo (annotate spikes such as ZA 1001 = 77 on 09-18) | No |
| Error sessions per 100 playback attempts, per code (attempts from the MEC-8/MEC-2 CSV) | No, once MEC-2 exists |
| New-code detection (first date a code is non-zero, like 1006 on 09-22) | No |
| Sessions with any error per day (no per-code sum) | Yes |
| Session-grain, 09-30 and table-boundary checks, reference vs `_sept26` | Yes |
| VSF vs `PLAYER_ERROR` overlap | Yes |

**Tests (no network, no real external services):**
- `test_shaka_session_artifact_selects_runner` — `--artifact shaka-error-session` calls the shaka session runner with the expected `--date`/`--tenant`/`--output-dir` argv.
- `test_shaka_session_artifact_passes_sept26_table_per_opco` — each OpCo's argv carries `--table <id>_ccl_debug_events_sept26` with that OpCo's Athena id.
- `test_shaka_session_artifact_covers_every_date_and_opco` — a 30-day month x 4 OpCos yields 120 calls.

**Commit:** `feat(mec): add September shaka-error-session to month orchestrator`

---

## MEC-14 — Reconcile Shaka error sessions with `unified_sessions` PLAYER_ERROR (all OpCos)

**Why:** MEC-13 counts distinct sessions per Shaka error code from the debug table; `unified_sessions` records `PLAYER_ERROR` as an `endreason`. A first ZA check (2026-09-04/15/18, see MEC-13
"Measured findings") showed the debug sessions are a superset of the unified `PLAYER_ERROR` sessions (11/35/142 vs 12/36/145). This task measures that gap per day for all four OpCos and classifies the
difference, so any error-code story states which of the two sources it quotes. Depends on MEC-13 (the CSV to reconcile) and is independent of MEC-3.

**Reference-review finding (ZA, fresh Athena counts 2026-10-11):** the unified `PLAYER_ERROR` count is exactly VSF plus play-stage errors, with no overlap: 09-15 = 27 (`REQUEST_VIEWING`) + 8 (`PLAY`)
= 35, and 09-18 = 131 + 11 = 142. So the 11/35/142 vs 12/36/145 gap is a debug-table-only remainder (1 to 3 sessions per day), not a VSF-versus-error mismatch. The CSV therefore reports unified
`PLAYER_ERROR` as VSF + play-stage (the existing `unified_pe_request_viewing` and `unified_pe_play` columns), then the debug-only remainder, and adds agreement statistics for the trust chart: per-day
paired difference and ratio of debug error sessions to unified `PLAYER_ERROR` sessions, with their median and maximum over the month (computed by the MEC-18 helpers). Rates quoted per 100 attempts
(VSF) and per 100 ended plays (play-stage), as in MEC-8.

**Classification evidence (ZA 2026-09-04/15/18, `_sept26`, Athena 2026-10-11; counts only).** Each distinct debug `PLAYER_ERROR` session joined on `parent_session_id = $.sessionid` (`event_start`
window 09-03..09-20); the classes are disjoint and ordered 1 to 4:

| Class | 09-04 / 09-15 / 09-18 | Unified rows | Error vs last unified `event_end` | Reading |
|---|---|---|---|---|
| 1 VSF (error before first frame) | 5 / 27 / 131 | `REQUEST_VIEWING`/`PLAYER_ERROR` | 0 s | legitimate; 11 / 27 households on 09-15 / 09-18 |
| 2 VPF-like (`PLAY`/`PLAYER_ERROR`) | 6 / 8 / 11 | `PLAY`/`PLAYER_ERROR` + `RV`/`PLAYING` | median 0-1 s; outliers -27 to -29 s, one -427 s | legitimate VPF-proxy; errors 2-983 s after `PLAY` start |
| 3 other end reason | 1 / 1 / 2 | `RV`/`PLAYING`, `BUFFERING`/`PLAYING`, `RV`/`DESTROY` (RV = `REQUEST_VIEWING`); no `PLAY` row | -31, -26, -27, -120 s | not a data fault; error after last row |
| 4 absent from `unified_sessions` | 0 / 0 / 1 | none in the window | n/a | candidate data fault, cause unproven; 6 events of code 1003 at one millisecond (09-18 08:08:19.983Z), mid-day |

Error codes (sessions / events): class 1 has 1001 76/82, 6001 49/77, 6006 13/16, 6002 10/16, 1003 8/19, 3016 4/4, E31012 4/4; class 2 has E31012 8/17, 1001 7/15, 1003 4/14, 3016 4/4, 3014 2/2, 3015
1/1; class 3 has 1001 2/7, 1003 1/6, E31012 1/6 (no 3xxx or 6xxx); class 4 has 1003 only. Classes 1 + 2 reproduce unified `PLAYER_ERROR` exactly (11/35/142); classes 3 + 4 are the 1/1/3 extra.

**Reconciliation rule:** unified `PLAYER_ERROR` = debug error sessions that carry `REQUEST_VIEWING`/`PLAYER_ERROR` or `PLAY`/`PLAYER_ERROR`; the debug superset adds the class 3 and 4 sessions (8% / 3%
/ 2% of debug sessions on these days). Recovery is not supported: class 3 errors arrive after the unified session's last row, so a session that "errored but kept playing" is not what the timing shows.
Working hypothesis (untested): the debug error is logged after unified closed the session (stall, then heartbeat loss), so those plays never got a closing `PLAY` row. Untested assumptions: that
unified `event_end` is the last heartbeat and that debug `datetime` is on the same clock. Only 4 class-3 sessions; MEC-22 widens the evidence.

**Files to change / create:**
- `queries/athena/mtn-monthly-shaka-vs-unified-error-sessions.sql` — catalog entry per `docs/guides/query-catalog.md`; reuse `ctap-smvod`'s `render_query` and `resolve_tenant_context(code,
  table_suffix="sept26")`.
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_error_reconciliation.py` — thin orchestrator (per-date x per-OpCo, same pattern as MEC-0/MEC-9).
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_error_reconciliation.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md`

**What to implement:**

1. Per day and OpCo, with the grain `COUNT(DISTINCT $.sessionid)` (debug table `<id>_ccl_debug_events_sept26`, `eventid = 'PLAYER_ERROR'`, `datetime` window) and `COUNT(DISTINCT parent_session_id)`
   (`unified_<id>.unified_sessions`, `endreason = 'PLAYER_ERROR'`, any `event_type`), write `output/<OPCO>/daily/2026-09_shaka-vs-unified-errors.csv` with: `debug_error_sessions`,
   `unified_pe_sessions`, `unified_pe_play`, `unified_pe_request_viewing`, `vsf_sessions`, `debug_in_unified_pe`, `unified_pe_in_debug`, `debug_only_other_endreason` and `debug_only_absent` (counts,
   no ids).
2. Classify each debug-only session (in the debug table, not in unified `PLAYER_ERROR`) by its `unified_sessions` rows: another `endreason`/`event_type` pair, or no row in the window (a date-window of
   D-1..D+1 around the session date, so day-boundary effects are not read as absent). Also record `debug_only_absent` separately; it is the cleanest "missing from `unified_sessions`" signal.
3. `unified_pe_in_debug` must be reported, not assumed to be 100%; ZA on 3 days was 100% (11/35/142), unverified elsewhere.
4. Also settles MEC-13's open checks (b) 2026-09-30 (min/max `datetime` per table) and (c) reference vs `_sept26`, since the same query reads both tables.
5. The per-code columns are never summed to a session count in this CSV; the per-code view stays in MEC-13.
6. The first live full-month run is a separate go-ahead; resolve each tenant with `scripts/resolve_tenant.py --system athena --tenant <athena_id>` first. Do not commit `output/` files without
   approval.

**Tests (no network, no real external services):**
- `test_query_renders_for_month` — all placeholders resolve for each OpCo and month.
- `test_classification_buckets_are_disjoint` — a fixed in-memory sample: each debug-only session lands in exactly one of `other_endreason` or `absent`.
- `test_bad_month_fails` — an invalid month raises a clear error.

**CSV design (proposal; the final columns, including whether `debug_only_absent` is split by adjacent-day presence, are decided at the start of MEC-14, not now).** One row per day per OpCo, counts
only. Example, ZA 2026-09-18 (measured): `debug_error_sessions` 145; `unified_pe_sessions` 142; `unified_pe_play` 11; `unified_pe_request_viewing` 131 (equals VSF by definition, so no separate VSF
column); `unified_pe_in_debug` 142; `debug_only_other_endreason` 2; `debug_only_absent` 1; `shaka_code_sum` 146 (from the MEC-13 CSV); `multi_code_sessions` 1 (`shaka_code_sum -
debug_error_sessions`). Identity checks, failing loudly: `debug_error_sessions = debug_in_unified_pe + debug_only_other_endreason + debug_only_absent`; `unified_pe_in_debug = unified_pe_sessions`;
`unified_pe_play + unified_pe_request_viewing >= unified_pe_sessions` (a session could carry both types).

**How it helps the final analysis:**
- One definition per claim: "sessions that ended in a player error" uses unified; "sessions with any Shaka error" uses debug; the CSV gives the exact gap per OpCo-day so the two are never mixed.
- Per-code trends from MEC-13 reconcile to `debug_error_sessions` through `multi_code_sessions`, so each per-code chart states its own caveat.
- Rates per 100 attempts for both sources, using the MEC-8 attempts column (the normalised funnel view in `analysis-storytelling-framework.md`).
- Trust chart: the daily `debug_only_*` share shows how often an error event does not become the recorded end reason. That this reflects errors playback recovered from is a hypothesis to test, not a
  finding.
- Quality gate before any chart: flag a day where `unified_pe_in_debug` is below 100% or a table boundary appears (2026-09-30).

**Design changes from the classification evidence (proposed, decided at MEC-14 start):**
- Replace the single `debug_only_other_endreason` count with its `event_type`/`endreason` pair set, and add `median_error_minus_session_end_s` (negative means the error came after the last unified
  row), so "recovered" is replaced by the measured timing.
- Add a class-2 check: first error time minus the `PLAY` row `event_start`, reported as min/max seconds (ZA 3 days: 2 to 983, all after the first frame).
- `debug_only_absent` must come from an unwindowed `parent_session_id` lookup in `unified_sessions`, not only the D-1..D+1 window (see MEC-23); report the burst shape (events per session, distinct
  timestamps) beside it.

**Commit:** `feat(mec): add Shaka vs unified PLAYER_ERROR reconciliation`

---

## MEC-15 — Eventdata shape census per error code, then extend the flattener for the gaps

**Why:** `investigations/ctap-smvod/scripts/flatten_error_eventdata.py` flattens `PLAYER_ERROR` `eventdata` (output e.g. `investigations/ctap-smvod/output/GH/error_eventdata_flat/`). It is generic: a
common envelope (`errorcode`, `sessionid`, `position`, `errordescription`, `user_agent`, `app_version`, `playerstatesnapshot`, `networkdetails`/`shakastats`),
`shakaerror.{code,category,severity,handled,message,data[]}`, a 6007-style wrapper (nested Shaka error in `data[0]` with a double-encoded MDRM body) and 3xxx MEDIA errors (`data` = `[type, null,
pipeline status]`). Missing paths come out as blank cells, not errors, so a code whose `eventdata` has a different shape is flattened silently incomplete. The GH sample (Oct 4-7) covers 1001, 1002,
1003, 3016, 6001, 6006, 6007 and E31012 only; 3014, 3015, 4032, 6002, 6012, 7000 and 1006 have no sample there, and E31012 is not a Shaka error (20 columns vs 26-28 for the Shaka codes, likely no
`shakaerror`). These are observations, not verified gaps.

**Files to change / create (the flattener change is decided only after the census):**
- `investigations/mtn-monthly-error-code-analysis/docs/eventdata-shape-census.md` — the coverage table.
- A thin census script in this investigation's `scripts/` plus a pure key-path walker in its tests (shared helper if one already exists in `ctap-smvod` `scripts/lib/`); check `SCRIPTS.md` first.
- Only for gaps the census names: `investigations/ctap-smvod/scripts/flatten_error_eventdata.py` (decided: extend it there, not a parallel flattener) and its regression tests. Existing columns and
  outputs stay unchanged; `prompt.md` "Scope guard" allows this change only after the census.

**What to implement:**

1. Census per OpCo and `errorcode` (September `_sept26` table, a bounded sample of days; sample size decided at start, not assumed): the JSON key paths in `eventdata` with count and share populated,
   and the distinct `shakaerror.data[]` element shapes. Counts only, no household or device ids in the doc.
2. Compare each code's paths with the paths the flattener reads (read from the `flatten_row` source, not from memory). Report populated-but-unread paths and read-but-never-populated columns per code.
3. Only then decide, per code, whether existing columns suffice or a new handler is needed (for example E31012 without `shakaerror`). Any new column follows the 6007/3xxx pattern: a pure function plus
   a regression test with a real sample payload.
4. The first live Athena run is a separate go-ahead; resolve each tenant with `scripts/resolve_tenant.py --system athena --tenant <athena_id>` first.

5. Output layout (user preference, recorded; implemented in this task's flattener extension, not in this docs session): append each day's rows into one file per error code, for example
   `output/<OPCO>/error_eventdata_flat/3016.csv`, instead of one file per date (`<date>_3016.csv` today). Design points to settle at the start of MEC-15, not assumed now: (a) the flattener drops
   columns that are blank in every row of a day's per-code file, so the header would change as days are appended; either use a fixed per-code column set or rewrite the file when a new column appears
   (reuse `src/lib/csv_io/monthly_store.py` column-gap handling where it fits; it keys on a date column, not `messageid`); (b) idempotence: dedupe on `messageid` across days (the flattener already
   dedupes within a run), so a re-run or an overlapping day range does not double-append; (c) growth and scope: one file per code forever vs one per month (`2026-09_3016.csv`), given `raw_eventdata`
   makes rows large; (d) the `<date>_all.csv` file: keep, replace with an appended `all.csv`, or drop; (e) the existing dated files: leave in place or migrate, without changing their content; (f)
   these files hold household and device ids, so they are not committed without the user's approval. Evidence from the GH 3016 files (read-only look at row counts and headers, cell contents not
   parsed): `2026-10-06_3016.csv` has 1 row and 27 columns, `2026-10-08_3016.csv` 36 rows and the same 27, and `2026-10-09_3016.csv` 7 rows and 28 (adds `pipeline_status`), so the header does drift;
   the 44 rows (about 55 KB) are small enough for one file per code; 10-04, 10-05 and 10-07 have no 3016 file, which today cannot be told apart from a day that was not run. Recommendation, to confirm
   at MEC-15 start: one file per code per month (for example `2026-10_3016.csv`, matching the `2026-09_*.csv` naming), a fixed union header with blanks where a column is absent, `messageid` dedupe,
   and a small per-day manifest (date, tenant, rows per code) so an absent day is distinguishable from a day with no rows.

**GH 3016 reference-file findings (read 2026-10-11; `investigations/ctap-smvod/output/GH/error_eventdata_flat/` 10-06, 10-08, 10-09):**
- Generator: `run_athena_error_eventdata.py` (query `ctap-smvod-error-eventdata`, UTC-day window, all `PLAYER_ERROR` events) then `flatten_error_eventdata.py`; one row is one event (`messageid`).
- 3016 is Shaka `MEDIA.VIDEO_ERROR` (category 3, severity 2, not handled, app text E83016 "cannot be played on your current device"), not webview, not DRM, `position` 0 (a real zero, start stage).
  `media_error_type` 4 is read as `MEDIA_ERR_SRC_NOT_SUPPORTED` (an interpretation, not documented in the repo).
- Rows / sessions / households: 1/1/1, 36/36/8, 7/7/5 (10-08 is concentrated, about 4.5 sessions per household). Header 27, 27, 28 columns: `pipeline_status` exists only when populated, because the
  flattener drops all-blank columns; this is the header drift that needs a fixed union header.
- Athena check (`is1aldzq_ccl_debug_events`): 10-06 1 row; 10-07 none; 10-08 45 raw rows, 36 distinct `messageid` and 36 sessions, 8 clients. The 9 duplicate rows make the `messageid` dedupe mandatory
  (a raw count over-counts by 25%).
- The 10-04 `_all` file has 0 rows for every code, and 10-05 and 10-07 have no 3016 (only 1003 and E31012), so a day with no file cannot be told apart from an unrun or empty day: the per-day manifest
  is justified.
- Not answered by the sample: cross-day dedupe behaviour, whether to keep `<date>_all.csv`, and migration of the dated files.
- `investigations/ctap-smvod/output/` is untracked and not git-ignored while it holds household and device ids; add an ignore rule (separate approval) before any `git add` near it.

**Tests (no network, no real external services):**
- `test_key_path_walker_lists_nested_paths` — a fixed sample payload yields the expected paths and counts.
- `test_unread_paths_reported` — a payload with an extra path is reported as populated-but-unread.
- Append layout: `test_append_adds_new_day_rows_to_code_file`, `test_rerun_same_day_does_not_duplicate_messageids` and `test_new_column_on_later_day_keeps_header_consistent`.
- For any flattener extension: one happy-path and one missing-path test per new handler, plus a test proving existing outputs are unchanged.

**Commit:** `docs(mec): add eventdata shape census` (and `feat(ctap-smvod): flatten <code> eventdata` if the flattener is extended)

---

## MEC-16 — Conviva comparison table per OpCo

**Why:** the reference review found that VSF is identical under Conviva's definition, VPF changes denominator, and the "unexplained" residual disappears (ZA September, fresh counts: VSF 765 = 15.2% of
5,029 attempts either way; play-stage errors 3.2% of attempts but 4.4% of ended plays; residual 582 = 319 no-end plays + 161 play-stage errors + 102 timeouts, none start failures). A reader needs that
comparison for every OpCo, not only ZA. Conviva's definitions (`docs.conviva.ai` metric dictionary: Attempts, Plays, Ended Plays, VSF, EBVS, VPF) are a naming and denominator reference, an analogy,
not a spec. Depends on MEC-8 and MEC-5.

**What to implement:** a pure comparison function plus a thin script that writes `output/<OPCO>/2026-09_conviva-comparison.csv` with one row per metric: our current definition and value, the
Conviva-aligned definition and value, and whether the number changes. Metrics: attempts, plays, VSF, EBVS (broad shared rule vs `REQUEST_VIEWING`/`DESTROY`; the ZA difference is unmeasured on fresh
data), ended plays, VPF-proxy, residual. Counts and rates only; each rate names its denominator.

**Tests:** `test_vsf_value_unchanged_under_conviva`, `test_vpf_proxy_uses_ended_plays`, `test_residual_decomposes_into_noend_vpf_timeout`.

**Commit:** `feat(mec): add Conviva comparison table`

---

## MEC-17 — Startup time, High Startup Time and EBVS abandonment

**Why:** Conviva's VST is the attempt-to-first-frame time and High Startup Time is the share of plays over a threshold (10 s for SPI Good, 8 s for Best); abandonment is an EBVS whose wait exceeds the
threshold. `unified_sessions` has a `REQUEST_VIEWING` `event_start`/`event_end` per session. ZA September, fresh counts: plays average 6.4 s (median 5.1, 90th percentile 11.6), 539 of 3,967 (13.6%)
over 10 s; EBVS average 27.2 s (median 7.2), 117 of 296 (39.5%) over 10 s; VSF median 3.6 s. This task makes the daily series for all four OpCos. Depends on MEC-8.

**What to implement:** per-day count, average, median, 90th percentile and over-10 s / over-8 s counts of the `REQUEST_VIEWING` duration, split by `endreason` (plays, VSF, EBVS). First check that the
`REQUEST_VIEWING` duration equals attempt-to-first-frame (report, do not assume); SPI thresholds are Conviva's defaults and are parameters, not facts about this service.

**Tests:** `test_percentiles_on_fixture`, `test_threshold_counts`, `test_negative_or_null_duration_fails_loudly`.

**Commit:** `feat(mec): add startup-time and abandonment report`

---

## MEC-18 — Statistics helpers (confidence intervals, control chart, concentration, agreement)

**Why:** daily rates on thin days mislead (for example 83% on 48 attempts) and "outlier day" must be a rule, not an impression. Permanent, tested `scripts/` module under this investigation (no
throwaway code): Wilson interval for a rate; p-prime (overdispersion-adjusted) control limits for a daily rate varying with volume; concentration measures (top-N share, Gini, sessions per affected
household) for MEC-6/7; paired difference and ratio with median and maximum for MEC-14 agreement; Spearman for volume versus failure rate; day-of-week split. Households repeat attempts, so plain
binomial limits are too tight; month-over-month tests use a household cluster bootstrap.

**Tests:** one happy-path and one edge-case test per helper (zero attempts, one household, all-equal values); no network.

**Commit:** `feat(mec): add statistics helpers`

---

## MEC-19 — Business vs technical error classification

**Why:** Conviva separates business errors (configured, such as user limits and playback restrictions) from technical ones (VSF-B/VSF-T, VPF-B/VPF-T). The decision-maker needs what is fixable: for
example ZM 6007 (MDRM 6211, test device not allowed) is already a policy-style code. Blocked until the user supplies or confirms the per-code business/technical list; do not guess. Output: a per-code
mapping file and the rates split, per 100 attempts (start errors) and per 100 ended plays (play-stage errors). Depends on MEC-13.

**Tests:** `test_unmapped_code_fails_loudly`, `test_split_sums_to_total`.

**Commit:** `feat(mec): add business vs technical error split`

---

## MEC-20 — Plays with no end record and the mid-month shift to timeouts

**Why:** in ZA September 319 of 3,967 plays (8.0%) have no end record, varying from 0-1% (09-26, 09-27) to 22% (09-03, 09-04), while `play_timeout_sessions` (102 in the month) rises sharply from about
09-21. The reference sample shows no-end falling to 1-3 per day on 09-21..23 as timeouts rise to 13/9/9. Hypothesis (to test, not a finding): a change in how unfinished sessions are closed (expired
session recorded as `TIMEOUT` instead of left without an end). Conviva counts an expired session as an ended play, not a failure, so timeouts are demoted from the failure story. Report per day and
OpCo no-end plays, timeouts and their sum; the sum is the trend line until this is settled. Depends on MEC-8.

**Tests:** `test_noend_plus_timeout_is_series`, `test_zero_plays_day_does_not_divide_by_zero`.

**Commit:** `feat(mec): add no-end and timeout trend`

---

## MEC-21 — Approximate Rebuffering Ratio (optional)

**Why:** Conviva's Rebuffering Ratio is rebuffering time over play time plus rebuffering time, excluding the pre-first-frame buffering and paused time. `unified_sessions` `BUFFERING` rows give a rough
equivalent (`buffering_total_ms` is in the shared outcome SQL). Label it approximate; only worth building if the story needs a quality-of-playback beat beyond the funnel. Bitrate, frame rate, CDN, ISP
and ASN are not available and are out of scope.

**Tests:** `test_ratio_excludes_startup_buffering`, `test_zero_playtime_fails_loudly`.

**Commit:** `feat(mec): add approximate rebuffering ratio`

---

## MEC-22 — Month-wide, all-OpCo error-session classification (depends on MEC-14)

**Why:** the ZA 09-04/15/18 evidence (see MEC-14 "Classification evidence") has only 4 class-3 and 1 class-4 sessions. This task repeats the four-class join (VSF, VPF-like, other end reason, absent)
for every day of September and all four OpCos, so the "error logged after the session ended" hypothesis rests on more than 4 sessions. It also tests the clock assumption: distribution of debug
first-error time minus unified `event_end` for class 1 and class 2 (expected near 0 s) against class 3. Counts, seconds and error codes only; no ids. Per-day class counts, the per-class code table
(sessions and events, never summed to sessions) and household concentration (share of households, sessions per household). First run ZA month, then NG/ZM/GH, each a separate go-ahead.

**Tests:** `test_classes_are_disjoint_and_cover_all_debug_sessions`, `test_class_precedence_vsf_over_play_error`, `test_negative_gap_means_error_after_session_end`.

**Commit:** `feat(mec): classify debug error sessions against unified_sessions`

---

## MEC-23 — Absent debug error sessions: where are they?

**Why:** ZA 2026-09-18 has one debug error session (6 events of code 1003 at one millisecond, mid-day) with no `unified_sessions` row between 09-03 and 09-20. Query `unified_sessions` by
`parent_session_id` with no date window, check the same device and household in the debug and unified tables on the day, and count how many debug events share one `datetime` per absent session across
the month. Report causes as measured (outside the window, no unified row, a burst of identical timestamps), not assumed; do not call it a data fault until the lookup shows no row at any date.

**Tests:** `test_absent_is_decided_without_date_window`.

**Commit:** `docs(mec): record absent debug error session causes`

---

## MEC-24 — VPF-like check against Conviva's conditions (depends on MEC-22)

**Why:** class 2 sessions (`PLAY`/`PLAYER_ERROR`) are a VPF-proxy, not Conviva's VPF (`conviva-metrics-reference.md` section 3): the error must come after the first frame, the session must end, and
the error-to-end playing time must not exceed the last reported buffer length (150 s if none). ZA 3 days: every error is 2 to 983 s after the `PLAY` row start (after the first frame) and the
error-to-end gap is 0-1 s for most sessions. Measure per OpCo-day: error after `PLAY` start, error-to-end seconds, and the share within 150 s. Buffer length is not in `unified_sessions`, so state the
150 s fallback was used. Report as "VPF-proxy checked against the 150 s rule", never as VPF.

**Tests:** `test_gap_over_150s_is_not_vpf_like`, `test_error_before_play_start_is_not_vpf_like`.

**Commit:** `docs(mec): check VPF-proxy against Conviva conditions`

---

## MEC-25 — Business vs technical evidence profile per error code

**Why:** MEC-19 needs a per-code class, but the MTN business-error list is not in the repo. Until it arrives, each code gets an evidence profile from the flattened GH eventdata and a proposed class,
one code at a time with a decision at each step. Astro's Conviva exports (`data/reference/AstroErrorCode/`, account `c3.Astro-AstroGo`) are a reference only: they show that class is configured per
account (Astro files network errors 1001/1002 as business; 6001, 6006, 6007, 3015, 3017 as technical; 6008 in both; 3016, 1003 and E31012 absent) and give the export format to request for MTN.

**Method per code:** run `scripts/profile_error_code.py` and `scripts/summarize_error_devices.py` (`docs/usage.md` section 3), then record in `docs/error-code-classification-evidence.md`: distinct
values, events, sessions, households per day, concentration, `error_text`, Shaka and MDRM fields, timing (`position` 0 / >0, `player_phase`, `player_readystate`), `is_wv`, app and player versions, UA
family, the Astro key if any, the candidate class, confidence and what would settle it. Never print or commit ids; do not sum per-event measurements. A code whose text names a rule (device,
entitlement, concurrency, geo) leans business; a player, network, DRM or media code without policy text leans technical; mark undecided whenever the text alone cannot show it.

**Coverage (tick as done; sample file counts in `data/reference/GH/`):**
- [x] 3016 (3 days): leans business (device text, position 0), undecided; one 10-09 decode event is a counter-signal.
- [x] 1003 (5 days): leans technical (network text, mixed start and mid-play stage), undecided.
- [ ] 1001, 1002, 6001, 6006, 6007, E31012 (GH sample present).
- [ ] 3014, 3015, 4032, 6002, 6012, 7000, 1006 and any other code the September `_sept26` table shows (no GH sample; needs a flattened sample or an Athena read-only batch approved first, tenant
  resolved with `python scripts/resolve_tenant.py --system athena --tenant is1aldzq`).
- [ ] The same pass for ZA, NG and ZM once their flattened samples exist; each OpCo's list is its own account configuration.

**Tests:** none (docs only; the scripts have their own tests in `tests/test_error_scripts.py`).

**Output:** feeds MEC-19; also settles which rates each class splits (per 100 attempts for start errors, per 100 ended plays for play-stage errors) and whether the split needs `unified_sessions`.

**Commit:** `docs(mec): record business vs technical evidence per error code`

---

## MEC-26 — Astro Pulse exports as a business vs technical reference

**Why:** `data/reference/AstroErrorCode/` holds four Conviva Pulse exports for account `c3.Astro-AstroGo` (filter `CONTAINS Shaka`, 2025-10-11 to 2026-10-10): VSF-B, VSF-T, VPF-B, VPF-T by error code.
Class is configured per account, so this is a calibration reference for MEC-19, not an MTN classification. A small parser script in `scripts/` (with `mec_lib` helpers) reads the export blocks
(preamble, then dimension tables). Per error key: class, impacted attempts or ended plays and share; keys present in both B and T (6008 appears in both with the same text, so matching is finer than
code plus text, cause unknown); how the `Err-NNNN` suffix maps to the GH numeric `errorcode` (unverified assumption to test); and the exact export to request for MTN.

**Tests:** `test_parser_reads_dimension_table`, `test_parser_fails_loudly_on_missing_dimension`.

**Commit:** `docs(mec): add Astro business vs technical reference`

---

## MEC-27 — Device analysis per error code from user_agent

**Why:** `scripts/summarize_error_devices.py` already gives model, Android version and build per error code, split by `is_wv`. Only Android user agents carry a model; iPhone and Mac agents carry OS
and browser version only (3016 and 1003 events are almost all `(unparsed)`). Extend the script to report OS and browser version for non-Android agents, then record per error code which devices are
affected, concentration (households, sessions per household) and the unparsed share. Reuse, do not copy, the ctap-smvod WebView device report logic where an import is possible.

**Tests:** `test_ios_user_agent_yields_os_and_browser_version`, `test_unknown_user_agent_stays_unparsed`.

**Commit:** `feat(mec): add OS and browser version to error device summary`

---

## MEC-28 — is_wv analysis per error code (South Africa)

**Why:** every GH reference event (3016, 1003, 1001, 1002, 6001, 6006, 6007, E31012) has `is_wv` false, so GH shows no WebView behaviour. South Africa has WebView sessions: the ctap-smvod `SA` error
report has an `is_wv` column and `analyze_webview_devices.py` produces a per-model wv report (`output/SA/`, 2026-10-01 onward). The ZA September reference files in this investigation have no user
agent, so the source (the SA error reports, or a flattened ZA sample) is settled at the start of the task. Report per error code the `is_wv` share and wv vs non-wv outcomes, with sources and dates; no
ids.

**Tests:** none (docs only).

**Commit:** `docs(mec): record is_wv analysis per error code for South Africa`
