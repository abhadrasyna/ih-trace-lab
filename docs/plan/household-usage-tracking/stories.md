# Household usage tracking — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `docs/refactor/`. After each task: set `SHA:` on the task
> line + tick the box, update the story status summary, add one line to the session log.

Package layout for every task below: `src/pipelines/usage_tracking/` with one module per job, `scripts/` for the CLI, `tests/` for pytest, and a `README.md`. Every new package directory gets an
`__init__.py`. Every public function has type hints and one happy-path plus one error or edge test. No network in tests.

---

## UT-1 — Prior-art audit and design review (docs only)

**Files to change / create:**
- `docs/plan/household-usage-tracking/spec.md` — audit evidence table, decisions, module map, planned diagram (no task checkboxes).

**What to implement:**

1. Prior-art check. Search `SCRIPTS.md`, `docs/archive/functional-code-taxonomy/`, `src/lib/*`, `scripts/lib/`, `investigations/ctap-smvod/scripts/` and `docs/plan/shared-pipeline-runtime/` for
   existing code that already loads a roster, queries Athena per household, reads the sm-vod Lightstep export, or renders a Markdown table. List each hit and reuse or reject it with a reason.
2. Decide the report date and Lightstep source. Open one real ctap-smvod export (`investigations/ctap-smvod/data/lightstep/ZA/<date>_smvod*.csv`) and record whether it carries household id, device id,
   status code and trace id. If yes, Option A (D-2, read the export) is viable; if not, Option B (D-1, live Lightstep) or a mix. Record the user's choice; do not pick for them if it is still open.
3. Decide where `make_auth` and `make_athena_client` come from: import from `aws_access_cli.runtime`, or extract into `src/lib` as a separate follow-up task. State the dependency direction either way
   (pipelines depend on `src/lib`, never on another pipeline).
4. Confirm the debug-events table rule: current month is `<tenant>_ccl_debug_events`, an older month is `<tenant>_ccl_debug_events_<mon><yy>`; run `SHOW TABLES` once and record the exact naming and
   the cut-over day.
5. Write the module map with a one-way dependency graph: `roster` ← `athena_source`, `lightstep_source` ← `merge` ← `render` ← `scripts/run_daily_usage_report`. Name each Protocol seam and each
   exception class. Decide which flags are rule functions and where the idle threshold lives.
6. Author the planned structure diagram (`docs/refactor/architecture-diagrams.md`), tests excluded.

**Tests:** none (docs only).

**Commit:** `docs(plan): usage tracking design review`

---

## UT-2 — Roster file and loader

**Files to change / create:**
- `config/tracked_households.yaml` — tenant `ZA`; households with `hhid`, `label`, `track`, and `members` (`name`, `device_id`, optional `active_from`). Real values for the team-A household (Sai,
  Keertesh, Josiah, Fayaz); a placeholder entry for the second household with `track: false` until its ids are supplied.
- `src/pipelines/usage_tracking/roster.py` — frozen dataclasses `Member`, `Household`, `Roster`; `load(path) -> Roster`; `tracked(roster) -> list[Household]`.
- `src/pipelines/usage_tracking/errors.py` — `UsageTrackingError` and `RosterError`.
- `src/pipelines/usage_tracking/tests/test_roster.py`.

**What to implement:**

1. Parse YAML (JSON accepted by the same loader). Resolve the tenant through `config/tenants.yaml` via the existing registry; never copy tenant ids into the roster.
2. Validate and raise `RosterError` with the offending entry: duplicate `device_id` across the file, empty or missing `hhid`, unknown tenant, `track` not a boolean, a member without a device id.
3. Allow the path to come from `--config` or the `TRACK_CONFIG` environment variable, defaulting to `config/tracked_households.yaml`.
4. Keep `track: false` households in the loaded roster but return only `track: true` ones from `tracked()`.

**Tests (no network, no real external services):**
- `test_load_valid_roster_and_filters_untracked` — two households, one `track: false`; `tracked()` returns one.
- `test_duplicate_device_id_raises` — the same device id in two entries raises `RosterError`.
- `test_unknown_tenant_raises` and `test_json_config_loads` — error path and the JSON alternative.

**Commit:** `feat(usage): tracked-household roster loader`

---

## UT-3 — Athena source

**Files to change / create:**
- `queries/athena/usage-tracking-household-device-sessions.sql` — sessions for one household and a set of device ids in a date range (parent_session_id, device_id, event_type, event_start, event_end,
  content, content_id, content_desc, endreason, timestamp_formatted).
- `queries/athena/usage-tracking-household-all-devices.sql` — distinct `device_id` values with session counts and first-seen time for a household and date, with no device filter.
- `queries/athena/usage-tracking-playback-errors.sql` — `PLAYER_ERROR` rows (errorcode, message, position) from the debug-events table for given `clientid` values and a date range.
- `queries/athena/index.md` — entries for the three files.
- `src/pipelines/usage_tracking/athena_source.py` — `SessionSource` Protocol and an Athena-backed implementer taking an injected query runner.
- `src/pipelines/usage_tracking/tests/test_athena_source.py`.

**What to implement:**

1. Follow `docs/guides/query-catalog.md` for headers (Purpose, Tables, Params, Status, Source) and parameter placeholders. Scope every query by household id and device id together.
2. `fetch_sessions`, `fetch_household_devices` and `fetch_errors` return plain typed rows. `clientid` is built as `<deviceId>:<householdId>`; the debug table name is picked by date using the UT-1
   rule.
3. Fetch error detail only for devices or sessions whose `endreason` shows an error, not for every session.
4. Wrap the Athena client's exceptions into `AthenaSourceError`; log call start at DEBUG and success at INFO with row count and duration; parameters go through `redact_params()`.
5. Take the Athena client from the factory UT-1 chose; do not construct a client in this module.

**Tests (no network, no real external services):**
- `test_fetch_sessions_maps_rows` — a fake runner returns canned rows; the result carries content names and endreasons.
- `test_errors_fetched_only_for_errored_sessions` — the fake runner is not called for the error query when no session errored.
- `test_client_error_is_wrapped` — a raised client error surfaces as `AthenaSourceError`.
- `test_debug_table_name_by_month` — current month and an older month pick the right table.

**Commit:** `feat(usage): Athena session and error source`

---

## UT-4 — Lightstep source

**Files to change / create:**
- `queries/lightstep/usage-tracking-smvod-by-device.md` — template filtered by household id and device id, grouped by `sessionId`, `http.status_code`, `lightstep.trace_id` (only if UT-1 chose live
  queries or needs it for a gap-fill); `queries/lightstep/index.md` entry.
- `src/pipelines/usage_tracking/lightstep_source.py` — `RequestSource` Protocol and the implementer for the source chosen in UT-1 (export CSV reader, or `scripts/lib/lightstep_api.py` client
  injected).
- `src/pipelines/usage_tracking/tests/test_lightstep_source.py`.

**What to implement:**

1. Return per-device request count, 5xx count and the trace id per session for the report date, as plain typed rows.
2. If reading the export: use the existing CSV helpers and handle a missing file as `LightstepSourceError`, not an empty result. If live: use the EU key from `.env` through the existing token
   provider, reuse the slicing and auto-split, and never log the token.
3. Treat a household or device absent from the data as zero activity, distinct from a source failure.
4. Wrap source exceptions into `LightstepSourceError`; same logging contract as UT-3.

**Tests (no network, no real external services):**
- `test_counts_and_5xx_per_device` — canned rows produce the right counts.
- `test_missing_export_raises` (or `test_api_error_is_wrapped` for the live path).
- `test_absent_device_is_zero_not_error`.

**Commit:** `feat(usage): Lightstep request source`

---

## UT-5 — Pure merge and rule functions

**Files to change / create:**
- `src/pipelines/usage_tracking/merge.py` — per-person metrics and the household/day model.
- `src/pipelines/usage_tracking/rules.py` — one function per flag, collected in a list.
- `src/pipelines/usage_tracking/tests/test_merge.py`, `tests/test_rules.py`.

**What to implement:**

1. Build per person: active, sessions, watch minutes, errors, top content, Lightstep requests, 5xx, flags. A person with no data is idle, not missing.
2. Flags as rule functions `rule(household_day) -> list[Flag]`: idle (N days, N from one named constant), error endreason, Athena-versus-Lightstep mismatch by session id, and new device.
3. New device: any `device_id` returned by `fetch_household_devices` that is not in the household's `members`, reported only for `track: true` households, with first-seen time and session count.
4. 7-day trend: sessions per person per day over the trailing seven days, from one Athena window.
5. No I/O in these modules: inputs are plain rows, outputs are plain dataclasses, so adding a flag means adding a function and appending it to the list.

**Tests (no network, no real external services):**
- `test_person_metrics_and_idle_flag`.
- `test_new_device_flagged_on_tracked_household` and `test_untracked_household_never_flagged`.
- `test_mismatch_flag_when_session_only_in_athena`.
- `test_trend_has_seven_days_with_zeros`.

**Commit:** `feat(usage): usage merge and flag rules`

---

## UT-6 — Markdown report renderer

**Files to change / create:**
- `src/pipelines/usage_tracking/render.py` — `render_report(day_model) -> str`, satisfying `src/lib/report_render.protocols.ReportRenderer` where its row-of-strings shape fits; otherwise a pure
  function with a documented reason.
- `src/pipelines/usage_tracking/tests/test_render.py` and a small golden file under `tests/data/`.

**What to implement:**

1. Output exactly: title line with date and tenant; summary line (HHIDs, devices, active, sessions, errors); per household a table with Person, Device (first 8 chars), Active, Sessions, Watch min,
   Errors, Top content, Lightstep reqs, 5xx, Flags; per-person session detail (time, parent_session_id, content, endreason, outcome, error code and message for errored sessions only, trace_id); an
   Anomalies section; a 7-day Trend section.
2. HHIDs are shortened in headings (first 6 characters plus an ellipsis) with the label; full ids appear only in the Anomalies section where needed to act.
3. Keep file writing out of this module: it returns a string; the CLI writes it through the shared writer.
4. Markdown prose lines stay within 200 characters.

**Tests (no network, no real external services):**
- `test_render_matches_golden_report`.
- `test_render_no_activity_day` — all people idle still renders every section.

**Commit:** `feat(usage): daily usage report renderer`

---

## UT-7 — CLI, failure handling, docs and final diagram

**Files to change / create:**
- `src/pipelines/usage_tracking/scripts/run_daily_usage_report.py` — `main()` with `--date`, `--config`, `--out-dir`.
- `src/pipelines/usage_tracking/README.md` — schedule, inputs, outputs, failure behaviour, the cron line.
- `src/pipelines/usage_tracking/tests/test_run_daily_usage_report.py`.
- `SCRIPTS.md`, `CONTEXT.md` ("What Exists"), `docs/plan/TODOS.md`, and the after diagram under `docs/` generated from the tree with tests excluded.

**What to implement:**

1. The first statement of `main()` is `init_logging()`; bind one FCID with the slug `daily-usage-report`; log run start with date and config path, and run end with counts and outcome.
2. Wire: load roster, ensure Athena auth, fetch, merge, render, write `reports/usage/<date>.md`. Each source is injected so the wiring is the only place concrete clients are built.
3. On a failed SSO refresh or query: log the failure once, write `reports/usage/<date>.FAILED.txt` stating "report not generated" and why, and exit non-zero; never write a partial report as if
   complete.
4. A second run for the same date overwrites that date's report; there is no other state.
5. Document the cron line in the same style as the existing jobs, with the offset chosen in UT-1, for example `0 14 * * * cd $REPO && $PY -m src.pipelines.usage_tracking.scripts.run_daily_usage_report
   --date "$(date -v-2d +\%Y-\%m-\%d)" >> $LOGS/cron_usage_report.out 2>&1`. The user installs it.
6. Run once against real data for a recent date and have the user read the report before closing the task.
7. Regenerate the architecture diagram from the tree and compare it with the UT-1 plan; record any difference.

**Tests (no network, no real external services):**
- `test_main_writes_report_for_tracked_households` — fake sources, temp directory.
- `test_auth_failure_writes_failed_note_and_exits_nonzero`.
- `test_untracked_household_not_queried` — the fake runner never sees its ids.

**Commit:** `feat(usage): daily usage report CLI and docs`
