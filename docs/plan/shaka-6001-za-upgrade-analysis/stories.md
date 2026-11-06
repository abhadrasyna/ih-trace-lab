# Shaka 6001 ZA upgrade analysis — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`; reuse decisions in `spec.md`. After each task: set `SHA:` on
> the task line + tick the box, update the story status in `CONTEXT.md`, add one line to the session log.

## Common rules (every task)

- CLI scripts use `argparse` only (no hardcoded paths, dates or ids). Defaults come from `investigations/shaka-6001/config/analysis.yaml`; `--tenant` defaults to ZA.
- Paths come from `YamlPathResolver`: data in `investigations/shaka-6001/data/<tool>/ZA/`, outputs in `investigations/shaka-6001/output/ZA/`, charts via `write_chart_png` into `.../output/ZA/charts/`.
- Pure logic functions plus a thin `main()`; fail loudly on bad input; type hints on all public functions; `(str, Enum)` for string enums; every new package directory has an `__init__.py`.
- Logging: `init_logging()` is the first statement of every `main()`; Athena calls log start at `DEBUG` and success at `INFO` with a duration; params go through `redact_params`; a failure is logged
  once, at the layer that first catches it. Concurrent fetches carry the FCID with `contextvars.copy_context()` and have a test asserting it.
- External boundaries raise our own exceptions (config errors, fetch errors); yaml, boto3 and pandas exceptions never leak to callers.
- Athena access is injected as a `src.lib.athena.AthenaClient`; tests use a fake client, so no network. Every query used is a registered file under `queries/athena/` (query-catalog rules).
- Each task registers its scripts in `SCRIPTS.md` and its queries in `queries/athena/index.md` in the same commit.
- Rates always appear next to counts, and every output states its base (events, sessions or households) and tenant. Table timestamps are UTC; convert to IST before day or period logic.
- Cron-safe by design (the daily run reuses these scripts, never a copy): every script is non-interactive and idempotent (rerunning a date overwrites that date's outputs, never appends), takes
  explicit dates (`--date`, or `--start-date/--end-date`) with no reliance on "today" except in the runner, exits non-zero on failure, and uses absolute-path-free config only. Cron has a minimal
  `PATH`, no TTY and no SSO prompt, so Athena steps check AWS credentials first and fail fast with a clear message instead of waiting for a login. Cron does not catch up missed runs, so the runner
  backfills any date in the lookback window whose outputs are missing.
- `GUEST.*` ids are per-install, not real households or devices: keep them in their own cohort or table and say so.

---

## SU-1 — config loader and before/after classifier

**Files to change / create:**
- `investigations/shaka-6001/scripts/lib/analysis_config.py` — load and validate `config/analysis.yaml` into a frozen dataclass; raise `AnalysisConfigError` on any problem.
- `investigations/shaka-6001/scripts/lib/period.py` — `Period` (`str, Enum`: before, after, unknown) and `classify_period(ts_utc, app_version, config)`.
- `investigations/shaka-6001/tests/test_period.py`

**What to implement:**

1. Before: ts earlier than window start (IST) or version equals `before`. After: ts later than window end or version equals `after`.
2. Inside the window only the app version decides; a version matching neither gives `unknown`.
3. A timestamp and a version that disagree outside the window: the version wins and the row is flagged `conflict`.

**Tests (no network, no real external services):**
- `test_classifies_before_and_after_by_timestamp` — 16:29 IST before, 17:01 IST after, with UTC inputs.
- `test_window_uses_version_only` — 16:45 IST with each version, and with an unknown one.
- `test_missing_config_key_raises` — bad config raises `AnalysisConfigError`.

**Commit:** `feat(shaka-6001): add config loader and period classifier`

---

## SU-2 — shared libs in src/lib

**Files to change / create:**
- `src/lib/user_agent/` — promote `parse_user_agent` and `is_webview`; returns os_name, os_version, device_model, build_id, chrome_version, is_webview and `ua_shape` (`android_build`,
  `android_reduced`, `desktop`, `unparsed`).
- `src/lib/playback/` — `is_success(playback_outcome)`: true only for `DESTROY` (`EBVS` and `INCOMPLETE_NO_DESTROY` are not success).
- `src/lib/ranking/` — generalise `rank_households` into `rank_by_count(rows, key, *, top, tie_breakers)` with stable ties.
- `investigations/ctap-smvod/scripts/` — thin re-exports of the moved names so the existing `ctap-smvod` tests stay green.
- `docs/guides/functional-code-taxonomy.md` — add the three targets.
- `tests/lib/` tests for each module (follow the existing test layout for `src/lib`).

**Tests (no network, no real external services):**
- `test_parses_p11_webview_ua` — the P11 sample gives model `P11`, build `TP1A.220624.014`, Android 13, Chrome 156.0.8078.47, webview true.
- `test_non_wv_and_reduced_ua` — no `wv` gives webview false; `Android 10; K)` is `android_reduced`.
- `test_success_means_destroy_only`, `test_rank_by_count_stable_ties`.
- Run the `ctap-smvod` tests to prove the re-exports hold.

**Commit:** `feat(lib): promote user-agent, playback and ranking helpers`

---

## SU-3 — local-data loader and Athena fetch wrapper

**Files to change / create:**
- `investigations/shaka-6001/scripts/lib/local_data.py` — find and load daily files for a date range from the four local sources (order in `prompt.md`) and return rows plus the dates not found.
- `investigations/shaka-6001/scripts/lib/athena_fetch.py` — `fetch_missing(client: AthenaClient, query_name, dates, ...)`: runs the registered query for missing dates only, saves each date locally,
  raises `FetchError` on failure.
- `investigations/shaka-6001/tests/test_local_data.py`, `test_athena_fetch.py`

**Tests (no network, no real external services):**
- `test_loader_reports_missing_dates` — a gap in the range is reported, not skipped.
- `test_fetch_only_missing_dates` and `test_fetch_error_wraps_client_exception` — a fake client; saved file reused on the next call.

**Commit:** `feat(shaka-6001): add local-data loader and fetch wrapper`

---

## SU-4 — per-event enrichment table

**Files to change / create:**
- `investigations/shaka-6001/scripts/build_enriched_events.py` — flatten eventdata (promote the used functions from `debug_event_parser.py` into `src/lib/` as part of this task), add parsed user-agent
  fields and `period`.
- `investigations/shaka-6001/tests/test_build_enriched_events.py`

**What to implement:**

1. Output `<start>_<end>_shaka6001_enriched.csv`, deduplicated by messageid (the debug table has exact duplicates; see the query catalog).
2. Print counts of unparsed user agents and `unknown`/`conflict` periods instead of dropping rows.

**Tests:** `test_duplicates_removed_once`, `test_unparsed_ua_kept_and_counted`.

**Commit:** `feat(shaka-6001): build enriched 6001 events`

---

## SU-5 — before/after counts by webview and device model

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_before_after.py` and `tests/test_analyze_before_after.py`

**What to implement:**

1. 6001 events and distinct devices/sessions per period, split webview vs non-webview, and per model (and model+build), with each period's share and the change.
2. Output CSVs `<start>_<end>_6001_before_after_{webview,model}.csv`.

**Tests:** `test_webview_split_counts`, `test_empty_period_yields_zero_not_error`.

**Commit:** `feat(shaka-6001): add before/after 6001 analysis`

---

## SU-6 — Chrome/Android version and device-level cuts

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_versions_devices.py` and `tests/test_analyze_versions_devices.py`

**What to implement:**

1. 6001 by Chrome major version and Android version, before vs after.
2. Devices with `drmenabled` (from the debug table), devices that fail then succeed (using `is_success` from `src/lib/playback`), and devices seen both in webview and outside it.

**Tests:** `test_chrome_major_grouping`, `test_mixed_webview_device_flagged`.

**Commit:** `feat(shaka-6001): add version and device cuts`

---

## SU-7 — charts for SU-5 and SU-6

**Files to change / create:**
- `investigations/shaka-6001/scripts/chart_before_after.py` and `tests/test_chart_before_after.py`

**What to implement:**

Follow `docs/guides/chart-guidelines.md`: compute plot values in pure functions, then call `render_stacked_bar(normalize=True)` for webview vs non-webview share before/after (absolute totals in the
labels), a horizontal bar sorted descending for top models (6001 dominates, so no donut), and `render_signed_line` for the daily trend. Save with `write_chart_png`; catch `ChartError`, log it and
carry on. Every title states its base (events or sessions, ZA, date range).

**Tests:** `test_chart_values_from_counts`, `test_chart_error_does_not_raise`.

**Commit:** `feat(shaka-6001): add before/after charts`

---

## SU-8 — guest-login redirect fetch

**Why:** `event_source = 'guestLoginPrompt-redirect'` is new code meaning the user left the webview to log in through a new browser. Facts in `spec.md`.

**Files to change / create:**
- `queries/athena/fact-navigation-interactions-guest-login-redirect.sql` and `queries/athena/guest-redirect-debug-events.sql` — registered queries (headers and index entries per
  `docs/guides/query-catalog.md`).
- `investigations/shaka-6001/scripts/fetch_guest_login_redirects.py` and `tests/test_fetch_guest_login_redirects.py`

**What to implement:**

1. Fetch per date (partition on `timestamp_formatted`) into `<date>_guest_login_redirect.csv`: `user_id`, `device_id`, `device_type`, `uid`, `nav_event_time`, `timestamp_formatted`,
   `navigation_start_time`, `navigation_end_time`, `nav_step_num`, `nav_step_total`, `nav_start_event`, `nav_end_event`, `start_reason`, `end_reason`, `event_type`, `event`, `event_code`,
   `event_source`, `event_source_ex`, `event_source_ex_name`, `source_name`, `event_details`; dedupe exact duplicates.
2. Fetch the same guests' events from `e6auj7k7_ccl_debug_events` (join `clientid = device_id || ':' || user_id`, always with a `datetime` range) into `<date>_guest_redirect_debug_events.csv`:
   `datetime`, `clientid`, `eventclass`, `eventid`, `eventdata`. Check scan size before running a range.
3. Reuse local files for known dates; only missing dates query (SU-3 wrapper).

**Tests:** `test_only_missing_dates_trigger_query`, `test_debug_join_key_built_from_guest_ids`.

**Commit:** `feat(shaka-6001): fetch guest-login redirect events`

---

## SU-9 — guest-login redirect analysis

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_guest_login_redirects.py` and `tests/test_analyze_guest_login_redirects.py`

**What to implement:**

1. Convert `nav_event_time` UTC to IST. Classify each guest by `appversion` from its `APP_DISCOVERY` debug events (SU-1), not by timestamp alone: the first redirect on 2026-11-04 is 16:45 IST, inside
   the window, with the old version.
2. Report rows and distinct guest ids per day and per period; steps per guest (`nav_step_num`, `nav_step_total`, `nav_end_event`) to see whether the redirect ends the journey; the debug events just
   before the redirect (does 6001 or a webview user agent precede it); share of guests with a debug-table match.
3. Say in every output that guest ids are not real households; report whether a guest later has non-guest ids only as a measured match rate, never assumed.

**Tests:** `test_guests_classified_by_app_version_inside_window`, `test_guest_ids_counted_not_households`.

**Commit:** `feat(shaka-6001): analyse guest-login redirects`

---

## SU-10 — 6001 cohort and playback-outcome data prep

**Files to change / create:**
- `investigations/shaka-6001/scripts/build_6001_cohort.py` and `tests/test_build_6001_cohort.py`

**What to implement:**

1. Cohort: every device/household with at least one 6001 in the enriched events (SU-4); key from `clientid` (`<deviceId>:<householdId>`), with the period and webview flag of its first 6001.
2. Load `playback_outcome` per date from local `ctap-smvod` data and outputs first; run the registered `ctap-smvod-playback-outcome` query only for missing dates (SU-3) and save locally.
3. Output `<start>_<end>_6001_cohort.csv` and a coverage line: cohort members with no session rows are counted, not treated as failures.

**Tests:** `test_cohort_first_6001_and_period`, `test_missing_session_rows_reported`.

**Commit:** `feat(shaka-6001): build 6001 cohort and outcome data`

---

## SU-11 — 6001 recovery analysis

**Definition of success:** `is_success` (`playback_outcome == "DESTROY"`), already the project's rule via `ctap-smvod-playback-outcome` and `src/lib/playback`. Do not redefine it.

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_6001_recovery.py` and `tests/test_analyze_6001_recovery.py`

**What to implement:**

1. Per cohort member: successful sessions before the first 6001, after it, and on the same day; time from first 6001 to the next success; never-recovered flag. Report the same-session case (6001 then
   `DESTROY` in one `sessionId`) separately from the cross-session case.
2. Roll up: recovery rate by period, webview vs non-webview and device model, with counts next to rates; a 100% stacked bar (recovered vs not) per the chart guidelines.
3. Guests stay in their own cohort.

**Tests:** `test_same_day_and_cross_day_recovery_split`, `test_guest_cohort_kept_separate`.

**Commit:** `feat(shaka-6001): analyse recovery after 6001`

---

## SU-12 — daily top 10 households and devices hit by 6001

**Files to change / create:**
- `investigations/shaka-6001/scripts/rank_daily_top_impacted.py` and `tests/test_rank_daily_top_impacted.py`; ranking via `src/lib/ranking`.

**What to implement:**

1. For each day (IST by default, `--day-basis utc` optional, basis stated), rank households and devices separately by 6001 events; `--top` defaults to 10; ties break by distinct sessions, then id.
2. Columns: day, rank, id, 6001 events, distinct sessions, first and last 6001 time (IST), most common model and build, webview share, period and app versions seen. Add the SU-11 recovery flag when
   that output exists; leave it empty otherwise.
3. `GUEST.*` ids are ranked in their own table; rows with no household or device are counted, not dropped.
4. Outputs `<start>_<end>_6001_top{N}_households.csv` and `_devices.csv`; a sorted horizontal bar for the latest day and a line of the top 10's share of the day's 6001 volume.

**Tests:** `test_top_n_per_day_with_stable_ties`, `test_guest_ids_ranked_separately`, `test_day_basis_ist_vs_utc` (20:00 UTC lands on the next IST day).

**Commit:** `feat(shaka-6001): rank daily top impacted households`

---

## SU-13 — daily top 10 device models hit by 6001

**Files to change / create:**
- `investigations/shaka-6001/scripts/rank_daily_top_models.py` and `tests/test_rank_daily_top_models.py`; ranking via `src/lib/ranking`, day basis shared with SU-12.

**What to implement:**

1. Per day (same day basis as SU-12), rank models by 6001 events; `--top` defaults to 10. Build is a separate column, not part of the key.
2. Columns: day, rank, model, 6001 events, distinct devices, households, sessions, webview share, most-seen Android and Chrome versions, period and app versions. Ties: distinct devices, then name.
3. Add the model's total events or sessions that day so a rate sits next to the count; models under `--min-events` (default 20) are flagged, not hidden.
4. Unparsed shapes (reduced `K`, desktop, iOS) get their own labelled rows; `GUEST.*` events stay in the count (the model is on the event).
5. Output `<start>_<end>_6001_top{N}_models.csv`, a sorted horizontal bar for the latest day and a stacked bar per day of top models vs other.

**Tests:** `test_one_model_across_builds_is_one_row`, `test_unparsed_ua_gets_own_row`, `test_low_traffic_model_flagged`.

**Commit:** `feat(shaka-6001): rank daily top impacted device models`

---

## SU-14 — user tenure and stickiness vs success rate

**Question (Sunday meeting):** how old, in time since subscribing, are the active users, is there stickiness, and how does playback success differ between old and new customers.

**Decisions (user, 2026-11-06):**
- Tenure proxy: first-ever session date per household in Athena. This is first seen, not a subscription date; state the earliest retained date in every output and never call it a subscription date.
- Active user: a household with at least one session from 2026-10-01 (fixed; no local-data fallback). First seen is measured over the full retained history (my reading of "fix it from 1 October"; if
  first seen should also be floored at 2026-10-01, buckets above 31 days would be empty, so confirm before building).
- Buckets: 0-7d, 8-30d, 31-90d, 91-180d, plus `180d+` so no household is dropped.

**Files to change / create:**
- `queries/athena/` — registered first-seen query (query catalog rules; check scan size first).
- `investigations/shaka-6001/scripts/analyze_user_tenure.py` and `tests/test_analyze_user_tenure.py`

**What to implement:**

1. Per household: first-seen, last-seen, active days since 2026-10-01 and tenure at the end of the window. Guests are excluded from tenure and counted separately.
2. Per bucket: households, share, sessions, success rate (`is_success`, over sessions with a playback attempt) and, where SU-5 covers the period, 6001 households and rate.
3. Stickiness: share active on 7+ days and in more than one week; cohorts by first-seen week and how many remain active later.
4. Tenure of households with at least one 6001 vs none, before vs after the upgrade.
5. Charts: a 100% stacked bar of success/failure by bucket (totals in labels) and a sorted bar of active households per bucket.

**Tests:** `test_bucket_boundaries` (7, 8, 30, 31, 90, 91, 180, 181), `test_guest_ids_excluded_from_tenure`, `test_first_seen_floor_flagged_as_censored`.

**Commit:** `feat(shaka-6001): analyse user tenure vs success rate`

---

## SU-15 — step-registry runner, daily mode, docs and registry

**Files to change / create:**
- `investigations/shaka-6001/scripts/run_analysis.py` — a registry `dict` of named steps (SU-4 to SU-14), run in dependency order; a new analysis registers itself, never adds a branch.
- `investigations/shaka-6001/scripts/run_daily.py` — cron entry point on top of the runner (pattern: `ctap-smvod/scripts/run_daily_pipeline.py`).
- `investigations/shaka-6001/docs/usage.md`, `SCRIPTS.md`, `CONTEXT.md` — every script, its inputs and outputs, the local-data-first rule and the cron line.
- `investigations/shaka-6001/tests/test_run_analysis.py`, `test_run_daily.py`

**What to implement:**

1. `run_analysis.py`: `--start-date/--end-date` (config defaults), `--only` to pick steps; missing local dates are reported up front and the run stops before any Athena query unless `--fetch-missing`
   is passed. Re-running a range overwrites that range's outputs.
2. `run_daily.py`: no arguments needed. It targets the last complete UTC day (and the IST day it overlaps), backfills any date in `--lookback-days` (default 3) with missing outputs, passes
   `--fetch-missing`, and runs the full registry for the window from the config start date to that day so before/after totals and the tenure and trend views stay current.
3. Runs are one-at-a-time (a lock file; a second start exits cleanly), logged to `investigations/shaka-6001/logs/run-daily_<date>.log` with a 30-day prune, and end with a run summary block (OK /
   FAILED / NOT RUN per step). A step failure does not stop independent steps; any failure writes `<date>.FAILED.txt` and exits 1, so a half-built report is never mistaken for a good one.
4. Credentials: refresh or verify AWS SSO through `src.lib.auth` before the first Athena call; if it cannot, mark the Athena steps NOT RUN, still run the local-data steps and exit 1.
5. Cost guard: each fetch checks scan size against `--max-scan-gb` (default set in the config) and skips with a logged reason instead of running an expensive query unattended.
6. Documented crontab line, in the style of `ctap-smvod/docs/usage.md` §7g: set `PATH` for `aws`, pick a time after the UTC day ends (for example 13:00 IST), note that the machine must be awake and
   that installing the crontab is a human step.

**Tests:** `test_runner_stops_on_missing_dates_without_flag`, `test_only_selects_steps`, `test_steps_run_in_dependency_order`, `test_daily_backfills_missing_dates`,
`test_daily_second_instance_exits_on_lock`, `test_failed_step_writes_failed_marker_and_exit_1`.

**Commit:** `feat(shaka-6001): add analysis runner, daily mode and docs`
