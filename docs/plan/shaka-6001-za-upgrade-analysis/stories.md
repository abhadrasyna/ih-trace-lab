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
2. Summaries: rows and distinct guest ids per day and per period (before/after by `nav_event_time` in IST, window per config, no app version on this table so the window itself is `unknown`); steps per
   guest (`nav_step_num`/`nav_step_total`) to see whether the redirect is a dead end; the events that precede it, from the same `uid` journey in `fact_navigation_interactions`.
3. Join keys for later analysis, because the guest uuid is the only link: `device_id` against the `GUEST.*` ids in the 6001 events (`hhid`/`clientid`) and in Lightstep traces, and against
   `fact_navigation_interactions` rows from the same `uid` after the redirect, to see whether a guest later logs in. Report the match rate; do not assume it.
4. Save the extract locally first; later runs read the local file and only query missing dates.

**Tests (no network, no real external services):**
- `test_guest_ids_counted_not_households` — rows with `GUEST.` prefix are counted as guest ids and flagged as unmappable.
- `test_local_file_reused_for_known_dates` — only missing dates trigger a query.

**Commit:** `feat(shaka-6001): fetch guest-login redirect events`
