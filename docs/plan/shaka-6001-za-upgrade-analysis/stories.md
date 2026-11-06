# Shaka 6001 ZA upgrade analysis — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status in `CONTEXT.md`, add one line to the session log.

Common rules for every script: `argparse` only (no hardcoded paths or dates), defaults from `investigations/shaka-6001/config/analysis.yaml`, `--tenant` defaults to ZA, `init_logging()` at start, pure
logic functions plus a thin `main()`, fail loudly on bad input, outputs under `output/ZA/` (charts under `output/ZA/charts/`), no network in tests.

---

## SU-1 — config loader and before/after classifier

**Files to change / create:**
- `investigations/shaka-6001/scripts/lib/analysis_config.py` — load and validate `config/analysis.yaml` into a frozen dataclass.
- `investigations/shaka-6001/scripts/lib/period.py` — `classify_period(ts, app_version, config)` returning `before`, `after` or `unknown`.
- `investigations/shaka-6001/tests/test_period.py`

**What to implement:**

1. Before: ts earlier than window start (IST) or version equals `before`. After: ts later than window end or version equals `after`.
2. Inside the window only the app version decides; a version matching neither gives `unknown`.
3. A timestamp and a version that disagree outside the window: version wins and the row is flagged `conflict`.

**Tests (no network, no real external services):**
- `test_classifies_before_and_after_by_timestamp` — 16:29 IST before, 17:01 IST after.
- `test_window_uses_version_only` — 16:45 IST with each version, and with an unknown one.
- `test_missing_config_key_raises` — bad config fails loudly.

**Commit:** `feat(shaka-6001): add config loader and period classifier`

---

## SU-2 — shared user-agent parser and local-data loader

**Files to change / create:**
- `scripts/lib/user_agent.py` — promote `parse_user_agent` from `investigations/ctap-smvod/scripts/parse_debug_user_agents.py`; leave a thin re-export there so its tests stay green.
- `investigations/shaka-6001/scripts/lib/local_data.py` — find and load daily files for a date range from the local sources, in the order listed in `prompt.md`, and report missing dates.
- `investigations/shaka-6001/tests/test_user_agent.py`, `test_local_data.py`

**What to implement:**

1. Parser returns os_name, os_version, device_model, build_id, chrome_version, is_webview (`; wv)` token), plus `ua_shape` (`android_build`, `android_reduced`, `desktop`, `unparsed`).
2. Loader returns rows plus a list of dates not found locally; the caller decides whether to query `ccl_debug_events` (via the query catalog) for those dates and save the result locally.

**Tests (no network, no real external services):**
- `test_parses_p11_webview_ua` — the P11 sample gives model `P11`, build `TP1A.220624.014`, Android 13, Chrome 156.0.8078.47, webview true.
- `test_non_wv_and_reduced_ua` — no `wv` gives webview false; `Android 10; K)` is `android_reduced`.
- `test_loader_reports_missing_dates` — a gap in the range is reported, not silently skipped.

**Commit:** `feat(lib): share user-agent parser, add shaka-6001 loader`

---

## SU-3 — per-event enrichment table

**Files to change / create:**
- `investigations/shaka-6001/scripts/build_enriched_events.py` — flatten eventdata (reuse `ctap-smvod/scripts/lib/debug_event_parser.py`), add parsed user-agent fields and `period`.
- `investigations/shaka-6001/tests/test_build_enriched_events.py`

**What to implement:**

1. Output `output/ZA/<start>_<end>_shaka6001_enriched.csv`, deduplicated by messageid (the debug table has exact duplicates; see the query catalog).
2. Print counts of unparsed user agents and `unknown`/`conflict` periods instead of dropping rows.

**Tests (no network, no real external services):**
- `test_duplicates_removed_once` and `test_unparsed_ua_kept_and_counted`.

**Commit:** `feat(shaka-6001): build enriched 6001 events`

---

## SU-4 — before/after counts by webview and device model

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_before_after.py` and `tests/test_analyze_before_after.py`

**What to implement:**

1. 6001 events and distinct devices/sessions per period, split webview vs non-webview, and per model (and model+build), with each period's share and the change; show counts next to rates.
2. Output CSVs `output/ZA/<start>_<end>_6001_before_after_{webview,model}.csv`.

**Tests (no network, no real external services):**
- `test_webview_split_counts` and `test_empty_period_yields_zero_not_error`.

**Commit:** `feat(shaka-6001): add before/after 6001 analysis`

---

## SU-5 — Chrome/Android version and device-level cuts

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_versions_devices.py` and `tests/test_analyze_versions_devices.py`

**What to implement:**

1. 6001 by Chrome major version and Android version, before vs after.
2. Devices with `drmenabled` (from the debug table), devices that fail then succeed, and devices seen both in webview and outside it; reuse the logic in `ctap-smvod/scripts/analyze_wv_*` where
   possible.

**Tests (no network, no real external services):**
- `test_chrome_major_grouping` and `test_mixed_webview_device_flagged`.

**Commit:** `feat(shaka-6001): add version and device cuts`

---

## SU-6 — charts via shared chart layer

**Files to change / create:**
- `investigations/shaka-6001/scripts/chart_before_after.py` and `tests/test_chart_before_after.py`

**What to implement:**

Follow `docs/guides/chart-guidelines.md`: compute plot values in pure functions, call `render_stacked_bar(normalize=True)` for webview vs non-webview share before/after (absolute totals in the
labels), a horizontal bar sorted descending for top models (6001 dominates, so no donut), and `render_signed_line` for the daily trend. Save with `write_chart_png` to `output/ZA/charts/`; catch
`ChartError`, log it and carry on. Every title states its base (events or sessions, ZA, date range).

**Tests (no network, no real external services):**
- `test_chart_values_from_counts` and `test_chart_error_does_not_raise`.

**Commit:** `feat(shaka-6001): add before/after charts`

---

## SU-7 — one-command runner, docs and registry

**Files to change / create:**
- `investigations/shaka-6001/scripts/run_analysis.py` — runs SU-3 to SU-6 in order for `--start-date/--end-date` (defaults from config), with `--only` to pick steps.
- `investigations/shaka-6001/docs/usage.md`, `SCRIPTS.md`, `CONTEXT.md` — document every script, its inputs and outputs, and the local-data-first rule.
- `investigations/shaka-6001/tests/test_run_analysis.py`

**What to implement:**

1. The runner reports missing local dates up front and stops before any Athena query unless `--fetch-missing` is passed.
2. Re-running the same range overwrites that range's outputs.

**Tests (no network, no real external services):**
- `test_runner_stops_on_missing_dates_without_flag` and `test_only_selects_steps`.

**Commit:** `feat(shaka-6001): add analysis runner and docs`

---

## SU-8 — guest-login redirect extract

**Files to change / create:**
- `queries/athena/fact-navigation-interactions-guest-login-redirect.sql` — registered query (follow `docs/guides/query-catalog.md`, header and index entry in `queries/athena/index.md`).
- `investigations/shaka-6001/scripts/fetch_guest_login_redirects.py` — fetch per date, save to `investigations/shaka-6001/data/athena/ZA/<date>_guest_login_redirect.csv`, then summarise.
- `investigations/shaka-6001/tests/test_fetch_guest_login_redirects.py`

**Why:** `event_source = 'guestLoginPrompt-redirect'` is new code meaning the user left the webview to log in through a new browser. Probe on ZA (Athena, 2026-11-06): 1 row on 2026-11-02, 280 rows /
148 users on 2026-11-04, 608 rows / 315 users on 2026-11-05. Every `user_id` is `GUEST.<uuid>` and `device_id` is that same bare uuid, so rows cannot be mapped to a real hhid or device id; the
analysis therefore counts guest ids, not households, and says so in every output.

**Columns to fetch** (`timestamp_formatted` is only a date; `nav_event_time` is the event time): `user_id`, `device_id`, `device_type`, `uid`, `nav_event_time`, `timestamp_formatted`,
`navigation_start_time`, `navigation_end_time`, `nav_step_num`, `nav_step_total`, `nav_start_event`, `nav_end_event`, `start_reason`, `end_reason`, `event_type`, `event`, `event_code`, `event_source`,
`event_source_ex`, `event_source_ex_name`, `source_name`, `event_details`.

**What to implement:**

1. Query by date range (partition on `timestamp_formatted`), defaults from `config/analysis.yaml`; dedupe exact duplicate rows.
2. Timestamps: `nav_event_time` is UTC (confirmed: it matches the debug table `datetime`, which ends in `Z`); convert to IST before applying the window. Before/after by timestamp is not enough on the
   4th: the first redirect that day is at 11:15 UTC = 16:45 IST, inside the window, and its debug events still carry `appversion v2026.10.27.01`. So classify each guest by the `appversion` from the
   `APP_DISCOVERY` debug events of the same guest (SU-1 classifier), not by this table alone.
3. Same-guest debug lookup (probed 2026-11-06, ZA, 4-5 Nov): all 462 distinct redirect guests have events in `unified_e6auj7k7.e6auj7k7_ccl_debug_events`. Its `clientid` is `<uuid>:GUEST.<uuid>`, so
   join on `clientid = device_id || ':' || user_id`, always with a `datetime` range filter (each day scans about 650 MB). Fetch per guest `datetime`, `eventclass`, `eventid`, `eventdata` (app version,
   screens, errors incl. 6001, user agent) into `investigations/shaka-6001/data/athena/ZA/<date>_guest_redirect_debug_events.csv`.
4. Summaries: rows and distinct guest ids per day and per period; steps per guest (`nav_step_num`/`nav_step_total`, `nav_end_event`) to see whether the redirect ends the journey; the debug events just
   before the redirect (does 6001 or a webview user agent precede it); whether a guest later has non-guest ids (cannot be assumed, report the match rate).
5. Save the extract locally first; later runs read the local file and only query missing dates.

**Tests (no network, no real external services):**
- `test_guest_ids_counted_not_households` — rows with `GUEST.` prefix are counted as guest ids and flagged as unmappable.
- `test_local_file_reused_for_known_dates` — only missing dates trigger a query.

**Commit:** `feat(shaka-6001): fetch guest-login redirect events`

---

## SU-9 — 6001 users and successful playback

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_6001_recovery.py` and `tests/test_analyze_6001_recovery.py`
- `investigations/shaka-6001/scripts/lib/playback_success.py` — reuse the project's definition; do not redefine it.

**Definition of success (already in the project):** a session is a confirmed success when its `playback_outcome` is `DESTROY`. `playback_outcome` comes from the registered query
`ctap-smvod-playback-outcome` (`unified_sessions`, one row per `parent_session_id`: the `PLAY` row's `endreason`, else `EBVS` if any `DESTROY` exists, else `INCOMPLETE_NO_DESTROY`), consumed by
`_is_success` in `investigations/ctap-smvod/scripts/analyze_webview_devices.py`. Import that helper (or promote it with SU-2) so the three existing wv scripts and this one stay consistent.

**What to implement:**

1. Cohort: every device/household with at least one 6001 in the enriched events (SU-3); key `deviceId`/`householdId` from `clientid` (`<deviceId>:<householdId>`), with the period (SU-1) and webview
   flag (SU-2) of its first 6001.
2. Outcomes: load `playback_outcome` per date from local `ctap-smvod` data and outputs first, else run `ctap-smvod-playback-outcome` for the missing dates and save the result locally.
3. Per cohort member report: successful sessions before the first 6001, after it, and on the same day; time from first 6001 to the next success; never-recovered flag. Add the same-session case (6001
   then `DESTROY` in one `sessionId`) separately from the cross-session case.
4. Roll up: recovery rate by period, webview vs non-webview, and device model; counts next to rates; charts follow `docs/guides/chart-guidelines.md` (a 100% stacked bar of recovered vs not).
5. Guest ids (`GUEST.*`) have no real household or device, so keep them as their own cohort and say it in the output; do not merge them with real households. Report the share of the cohort with no
   `unified_sessions` rows rather than counting them as failures.

**Tests (no network, no real external services):**
- `test_success_means_destroy_only` — `EBVS` and `INCOMPLETE_NO_DESTROY` are not success.
- `test_same_day_and_cross_day_recovery_split` and `test_guest_cohort_kept_separate`.

**Commit:** `feat(shaka-6001): analyse recovery after 6001`

---

## SU-10 — daily top 10 households and devices hit by 6001

**Files to change / create:**
- `investigations/shaka-6001/scripts/rank_daily_top_impacted.py` and `tests/test_rank_daily_top_impacted.py`

**Reuse first:** `investigations/ctap-smvod/scripts/rank_households_by_error.py` already ranks households by error; read it and import or promote its ranking logic (with SU-2) instead of rewriting it.

**What to implement:**

1. For each day in `--start-date/--end-date` (IST day by default, `--day-basis utc` optional; state the basis in the output), rank households and devices separately by 6001 event count from the
   enriched events (SU-3). `--top` defaults to 10.
2. Columns: day, rank, householdId or deviceId, 6001 events, distinct sessions, first and last 6001 time (IST), most common device model and build, webview share of its 6001 events, the period (SU-1)
   and app version(s) seen that day. Ties break by distinct sessions, then id, so reruns are stable.
3. `GUEST.*` ids are ranked in their own table, because they are per-install, not real households; say so in the output. Rows with no household or device are counted, not dropped.
4. Add each ranked id's recovery flag from SU-9 (did it have a `DESTROY` session after its first 6001) when that output exists; leave the column empty otherwise, never guess.
5. Outputs: `output/ZA/<start>_<end>_6001_top{N}_households.csv` and `_devices.csv`, one stacked set per day. A chart (horizontal bar, sorted descending, per guidelines) for the latest day, plus a
   share-of-total line showing how concentrated the 6001 volume is in the top 10 each day.

**Tests (no network, no real external services):**
- `test_top_n_per_day_with_stable_ties` and `test_guest_ids_ranked_separately`.
- `test_day_basis_ist_vs_utc` — an event at 20:00 UTC lands on the next IST day.

**Commit:** `feat(shaka-6001): rank daily top impacted households`

---

## SU-11 — user tenure and stickiness vs success rate

**Files to change / create:**
- `investigations/shaka-6001/scripts/analyze_user_tenure.py` and `tests/test_analyze_user_tenure.py`
- `queries/athena/` — registered query for first-seen date per household (query catalog rules).

**Question (for the Sunday meeting):** how old, in time since subscribing, are the active users, is there stickiness, and how does playback success differ between old and new customers, so the wider
impact of failing vs succeeding customers is clear.

**Decisions (user, 2026-11-06):**
- Tenure proxy: first-ever session date per household in Athena (no subscription-date column was found in the known tables). This is left-censored: a household first seen at the start of retained data
  is not necessarily new. State the earliest date of retained data in every output and never call the proxy "subscription date".
- Active user: a household with at least one session from 2026-10-01, or from the earliest date with data in the local folders if that is later.
- Buckets: 0-7d, 8-30d, 31-90d, 91-180d; households older than 180 days go into an extra `180d+` bucket (added so no household is dropped; the user's list stopped at 180).

**What to implement:**

1. Per household: first-seen date, last-seen date, active days in the window, tenure at the end of the window. Guest ids (`GUEST.*`) have no stable household, so keep them out of tenure and report
   their count separately.
2. Per bucket: households, share of active households, sessions, success rate (`playback_outcome = DESTROY` per SU-9's shared definition, over sessions with a playback attempt) and, where SU-4's data
   covers the period, 6001 households and rate. Counts next to rates.
3. Stickiness: share of each bucket active on 7+ days and in more than one week of the window; and cohort by first-seen week, showing how many are still active in later weeks.
4. Success vs failing: tenure distribution of households with at least one 6001 vs those with none, and before vs after the upgrade (SU-1), to show whether new or old customers are hit more.
5. Outputs under `output/ZA/` plus charts per guidelines: a 100% stacked bar of success/failure by tenure bucket (absolute totals in labels) and a sorted bar of active households per bucket. The query
   for first-seen needs the full retained history; use a `timestamp_formatted` lower bound that is stated in the output and check scan size before running.

**Tests (no network, no real external services):**
- `test_bucket_boundaries` — 7, 8, 30, 31, 90, 91, 180 and 181 days land in the right bucket.
- `test_guest_ids_excluded_from_tenure` and `test_first_seen_floor_flagged_as_censored`.

**Commit:** `feat(shaka-6001): analyse user tenure vs success rate`

---

## SU-12 — daily top 10 device models hit by 6001

**Files to change / create:**
- `investigations/shaka-6001/scripts/rank_daily_top_models.py` and `tests/test_rank_daily_top_models.py`
- Share the day-basis and ranking helpers with SU-10 (`scripts/lib/`), do not copy them.

**What to implement:**

1. Per day (IST by default, `--day-basis utc` optional, basis stated in the output), rank device models by 6001 events from the enriched events (SU-3); `--top` defaults to 10. Model comes from the
   shared user-agent parser (SU-2), and build is shown as a separate column, not part of the key, so one model is not split across builds.
2. Columns: day, rank, model, 6001 events, distinct devices, distinct households, distinct sessions, webview share, Android and Chrome versions most seen, and the period (SU-1) and app versions seen
   that day. Rank by events; ties break by distinct devices, then model name.
3. Normalise: add the model's total events or sessions that day (from the same data) so a rate sits next to the count; a big model with a small share is not the same as a small model failing often.
   Models with too little traffic (`--min-events`, default 20) are flagged, not hidden.
4. Unparsed and `unknown` shapes (reduced `K`, desktop, iOS) get their own labelled rows instead of being dropped, and `GUEST.*` events are kept in the count (the model is on the event, not the id).
5. Outputs: `output/ZA/<start>_<end>_6001_top{N}_models.csv`; a sorted horizontal bar for the latest day and a stacked bar per day of top models vs other, following the chart guidelines.

**Tests (no network, no real external services):**
- `test_top_n_models_per_day_stable_ties` and `test_one_model_across_builds_is_one_row`.
- `test_unparsed_ua_gets_own_row` and `test_low_traffic_model_flagged`.

**Commit:** `feat(shaka-6001): rank daily top impacted device models`
