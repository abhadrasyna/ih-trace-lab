# Video Start Failures Technical — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: every build task (CMR-VSFT-2 to CMR-VSFT-7) ships its tests in the same commit, offline (no network, fixtures built in the test). Confirm scope and plan with the user before creating or editing
anything (project Steps 2-3).

**Build rule (user, 2026-10-27):** the scratch POC only validates that the metric is possible. Every formal script and helper is built while working the tasks, as tested code, not left for the end and
not run through MCP. Code specific to this story lives in `investigations/conviva-metrics/scripts/` (tests beside it, in the layout `../concurrent-plays/` CMR-CP-2 scaffolds), common code in
`src/lib/`. Before writing anything new, read the existing runners and helpers and reuse or enhance them. The pure modules in CMR-VSFT-2, 3 and 5 take plain parsed data, so they do not wait for the
shared loader; CMR-VSFT-6 wires them to the shared session loader, chart, breakdown and report helpers from `../concurrent-plays/` (CMR-CP-2, CMR-CP-6) and must not copy them.

**Design map (from `docs/refactor/design-principles.md`, `code-deduplication-and-taxonomy.md`, `python-hygiene-and-automation.md` and `docs/guides/functional-code-taxonomy.md`), applied to every build
task:** metric rules stay in `investigations/conviva-metrics/`, mechanisms used by more than one metric go to `src/lib/`. Each piece is a pure function with typed inputs and outputs and no file or
network I/O; `main()` only parses arguments and wires. Parameters (business codes, interval, bands, state names) travel in a frozen dataclass, never module constants. New behaviour is data or a
passed-in `Callable`, not a new branch (OCP). Pure modules never import report or chart code (DIP). Domain errors, not `SystemExit` or `print`; `setup_logging()` once in `main()`.

**Settled on 2026-10-27 (with the user, during the POC session and the story-creation session):**

1. Source rule: Conviva page (see `prompt.md`); a session is VSF when it has a `PLAYER_ERROR` before its first `PLAYING` and before `DESTROY`.
2. Attempt = `CREATE` on the date; the failure is bucketed at its first error; UTC day; 5-minute interval, an argument.
3. Classification: everything is VSF-T until the business-error list exists; `--business-codes` carries the list and defaults to empty. It will change later.
4. Report layout: option A (`2026-10-24_ZA_vsf-technical-error-summary-optionA.md`), approved as the final form: chart, headline, extended error-codes table, top 10 content, playback type, then
   per-code detail tables with parallel column pairs and a blank spacer column between the pairs.
5. Error-codes table columns: VSF-T sessions, % of VSF-T, % of attempts, impacted households, % of all households, sessions per household (over sessions that have a household), first and last failure
   (UTC). A session with several codes counts under each code, and the table says so.
6. Detail tables use the first error per session; WebView is shown for 6001 only; 3016's three pipeline-status spellings are merged; bandwidth is Shaka `estimatedbandwidth` in bands (the POC's guess,
   confirmed in CMR-VSFT-1) with a "no data" row.
7. No Conviva reference figure exists, so no match is claimed.
8. Story shape (revised 2026-10-27, user): build tasks first, one tested piece per task; no standalone "explain the missing sessions" task. Option B is not built.
9. Reconciliation is a bounded check, not a task: the attempts count against the attempts POC's `debug_states.csv` (3,954 against 3,901) and the overlap with `outcome_first_debug.csv` (2,101 against
   2,091) are recorded as a note in CMR-VSFT-2 and CMR-VSFT-6, and chased only if the user asks.

---

## CMR-VSFT-1 — Settle the open definition points and the report content

**Files:** this story's `prompt.md` (definition section), the approved report `2026-10-24_ZA_vsf-technical-error-summary-optionA.md` if its sections change, and the `../discussion-prompt.md`
Discussion log.

**What to settle with the user (discussion, no code):**

1. The business-error list (MEC-27): who owns it, where it will live (a config file per tenant is the proposal), and the rule for a session with both business and technical codes (the POC says any
   business code makes it VSF-B).
2. Errors after `DESTROY` or after the start window: drop them as the POC does, or add Conviva's 90 s late-error window.
3. A session that errors and then plays: confirm the error does not count if `PLAYING` follows; equal timestamps sort the error first.
4. Bandwidth: confirm Shaka `estimatedbandwidth`, the band edges (1, 3, 10 Mbps) and the "no data" row; whether `navigatorconnection.downlink` should fill 6001's empty bandwidth columns.
5. Which codes get a detail table (6001, 3016, 1003, E31012 today): a fixed list, or every code above a share threshold.
6. Chart: the 5-minute series, and whether the PNG is committed beside the report (the POC copied it into the story folder; plan folders should hold only `.md`) or stays in the gitignored `output/`
   with a link.
7. The error-codes table: whether to add a total row and a peak bucket column.
8. A Conviva VSF-T figure for ZA on 2026-10-24 to compare against, the tolerance that counts as a match, and the Conviva reporting timezone.

**Commit:** `docs(conviva-metrics): cmr-vsft-1`

---

## CMR-VSFT-2 — Build the VSF-T core

**Files:** a pure module `investigations/conviva-metrics/scripts/vsf_core.py` and `test_vsf_core.py`. Source of the logic: `scratch/2026-10-27_conviva-vsf-technical_timeseries_poc.py` (`create_time`,
`start_failure`, `bucket`, `series_points`).

**What to implement:**

1. A frozen `VsfRules` dataclass (business codes, interval minutes, state vocabulary: the `CREATE`, `PLAYING`, `DESTROY` and `PLAYER_ERROR` names) with validation.
2. `find_attempt(events, rules)` and `find_start_failure(events, rules)` returning typed `Attempt` and `StartFailure` values (first error time, the codes before start; a blank code is `(blank)`).
3. `classify(failure, rules)` returning VSF-T or VSF-B; a session with any business code is VSF-B, an empty list makes everything VSF-T.
4. `bucket_failures(failures, interval, day)` returning counts per bucket with empty buckets as gaps, taking the day length and interval as parameters.
5. A reconciliation note recorded in the module's docstring or the story: the POC gives 2,101 VSF-T on the ZA day; compare with `debug_states.csv` attempts (3,901) and `outcome_first_debug.csv`
   (2,091) and record the figures, without chasing the 53-session and 10-session differences.

**Tests (no network):**
- `test_failure_is_error_before_first_playing` — a `PLAYER_ERROR` at 10:00:03 before `PLAYING` at 10:00:10 is a start failure bucketed at 10:00:03.
- `test_error_after_playing_is_not_failure` — an error after `PLAYING` does not count.
- `test_error_after_destroy_not_failure` — an error after `DESTROY` does not count.
- `test_equal_timestamp_error_first` — shuffled rows with equal timestamps for `PLAYER_ERROR` and `PLAYING` give the same result, the error winning.
- `test_blank_error_code_counted` — a failure with a blank code is counted under `(blank)`.
- `test_business_code_makes_vsfb` — a session with any business code is VSF-B, the rest VSF-T; with an empty list everything is VSF-T.
- `test_attempts_only_with_create_on_date` — a session without `CREATE` on the date is not an attempt.
- `test_empty_bucket_is_gap` — a bucket with no failures has no value.
- `test_series_reconciles_with_total` — the bucket counts add up to the VSF-T total.
- `test_rules_validation` — an interval below one minute raises a clear error.
- `test_no_failures_error` — no start failures on the date raises a clear error.

**Commit:** `feat(conviva-metrics): vsf technical core`

---

## CMR-VSFT-3 — Build the error-codes table

**Files:** a pure module `investigations/conviva-metrics/scripts/vsf_error_codes.py` and `test_vsf_error_codes.py`. Source: `scratch/2026-10-27_conviva-vsf-technical_error-codes-table_poc.py`
(`code_rows`).

**What to implement:** `error_code_rows(failures, households, attempts, top)` returning typed rows with: code, VSF-T sessions, % of VSF-T, % of attempts, impacted households, % of all households,
sessions per household, first seen and last seen (UTC). A session with several codes counts under each. Sessions per household divides sessions that have a household by the distinct households. Also
return the household total and the count of VSF-T sessions without a household for the note under the table. The POC's ZA figures are the acceptance values (6001: 1,898 sessions, 358 households, 5.3
sessions each).

**Tests (no network):**
- `test_error_code_rows_multi_code` — a session with two codes counts under both; the rows do not have to add up to the total.
- `test_households_distinct_and_blank_excluded` — impacted households are distinct ids; sessions with no household count in sessions but not in households.
- `test_sessions_per_household_uses_household_sessions` — three sessions, one without a household, over two households give 1.0, not 1.5.
- `test_first_and_last_seen_are_utc` — the times come from the failure times, in UTC.
- `test_share_of_attempts` — the share equals the code's sessions over attempts.
- `test_rows_sorted_and_topped` — rows are sorted by sessions then code and cut at `top`.
- `test_no_household_in_data_error` — no household anywhere raises a clear error.

**Commit:** `feat(conviva-metrics): vsf technical error codes table`

---

## CMR-VSFT-4 — Build the flat error eventdata export

**Files:** an Athena query in the catalog (`docs/guides/query-catalog.md` rules), a runner `investigations/conviva-metrics/scripts/run_athena_error_eventdata.py` with tests, `SCRIPTS.md`. Source: the
existing `investigations/ctap-smvod/scripts/flatten_error_eventdata.py` (read-only; wrap it, do not edit it) and the Athena `error_eventdata` pull.

**What to implement:**
1. Read the existing runners first (`investigations/ctap-smvod/scripts/`, the CMR-CP-2 raw export runner) and reuse or enhance one if it already pulls `error_eventdata`.
2. A catalogued query for one tenant and one UTC day with the shared `day_bounds()`.
3. A runner with `--tenant`, `--date`, `--dry-run` and `--force`, resolving the tenant first (`docs/guides/tenant-resolution.md`), saving the raw export and the flattened CSV under the investigation's
   data folder, and refusing to overwrite without `--force`.
4. The flattened CSV keeps one row per `PLAYER_ERROR` with the columns the detail tables need: session id, time, error code, phase, network type, WebView flag, host, pipeline status, Shaka error,
   estimated bandwidth and downlink.

**Tests (no network):**
- `test_query_bounds_use_day_bounds` — the rendered query covers exactly the UTC day.
- `test_dry_run_writes_nothing` — `--dry-run` prints the plan and creates no file.
- `test_existing_export_not_overwritten_without_force` — a second run without `--force` stops with a clear message.
- `test_flat_row_per_player_error` — a fixture with two errors in one session gives two rows with the expected columns.
- `test_e31012_string_code_and_null_shaka` — a string error code and a null Shaka error flatten without an exception.

**Commit:** `feat(conviva-metrics): vsf technical error eventdata export`

---

## CMR-VSFT-5 — Build the per-code detail tables

**Files:** a pure module `investigations/conviva-metrics/scripts/vsf_detail.py` and `test_vsf_detail.py`, plus a `percentile()` helper in `src/lib/` (check first whether the video startup time story
already added one) with tests. Source: `scratch/2026-10-27_conviva-vsf-technical_error-bandwidth_poc.py` and the option A tables.

**What to implement:**
1. `group_first_errors(flat_rows, failures)` returning one row per VSF-T session at its earliest error.
2. A frozen `BandwidthBands` value (edges in `VsfRules`, default 1, 3, 10 Mbps) and `band(value, bands)`; blank, NaN and negative values are "no data".
3. `detail_table(rows, columns)` returning rows for parallel column pairs (phase, network, a per-code third pair, bandwidth) with a blank spacer column between the pairs. A per-code column spec (data,
   not branches) says 6001 gets WebView, 3016 pipeline status (the three spellings merged) and 1003 host; the other codes get none.
4. Percentiles p50 and p90 over the valid bandwidth values and the count of sessions with data, shown under each table, plus the dominant Shaka error text for the code.

The acceptance values are the approved option A tables on the ZA day.

**Tests (no network):**
- `test_group_first_errors_picks_earliest` — a session with two error rows is grouped under the earlier code.
- `test_pipeline_status_spellings_merged` — the three 3016 spellings become one group.
- `test_bandwidth_band_edges` — 0.99, 1.0, 3.0 and 10.0 Mbps fall into the right bands; NaN, negative and blank are "no data".
- `test_percentile_nearest_rank` — p90 of ten values is the ninth, never the maximum; a group of one or two is never below the median.
- `test_percentile_ignores_invalid_values` — NaN and negative values are excluded from the percentile and from `n`.
- `test_detail_table_has_spacer_columns` — the rendered rows have a blank column between each pair and the same cell count in every row.
- `test_webview_column_only_for_6001` — other codes' detail tables do not carry the WebView pair.
- `test_no_data_row_counts` — the "no data" row equals the sessions without a valid bandwidth.

**Commit:** `feat(conviva-metrics): vsf technical detail tables`

---

## CMR-VSFT-6 — Build the report and the script, retire the scratch POCs (needs CMR-CP-6)

**Files:** the script `investigations/conviva-metrics/scripts/run_vsf_technical.py`, a report writer `vsf_report.py` with tests, a chart renderer in `src/lib/charts/` only if the shared line renderer
from CMR-CP-6 lacks a count axis (with tests), Athena catalog entries only for inputs added here, `SCRIPTS.md`; retire the three scratch copies per `scratch/SCRATCH.md`.

**What to implement:** wire the CMR-VSFT-2, 3 and 5 modules to the shared session loader, breakdown helper and report writer from CMR-CP-6, and the saved exports from CMR-CP-2 and CMR-VSFT-4.
1. The report in the option A layout: title and definition with the Conviva link, chart, headline, error codes, top 10 content, playback type, then the detail tables with the spacer columns. The chart
   image follows the CMR-VSFT-1 decision.
2. Playback type from the raw `contenttype` field (the POC guessed from the session-id prefix), and the device split from the CMR-CP-5 sources; any gap is recorded as a blocker in the report.
3. `--tenant`, `--date`, `--interval`, `--business-codes`, `--bands`, run on demand and in a daily run (the batch entry a scheduler calls for one date).
4. The script reproduces the approved ZA 2026-10-24 option A report (2,101 VSF-T, 53.1%), then the scratch copies are retired.

**Tests (no network):**
- `test_summary_rate_is_failures_over_attempts` — the share equals failures divided by attempts.
- `test_report_sections_in_order` — the report has the option A sections in order.
- `test_report_content_reconciles` — each breakdown table plus its Unresolved row equals the VSF-T total.
- `test_report_states_no_reference_figure` — the report says no Conviva figure is held.
- `test_daily_run_uses_given_date` — the daily entry runs for the date it is given and writes one report.
- `test_missing_export_error` — a missing saved export gives a clear message naming the runner to run.

**Commit:** `feat(conviva-metrics): graduate vsf technical poc`

---

## CMR-VSFT-7 — Prove it generalises

**Files:** the script and a short note on any per-tenant state-name or column differences.

**What to implement:** run for one more tenant with Athena debug events and error eventdata (GH or ZM; check what exists locally first, otherwise fetch with the CMR-CP-2 and CMR-VSFT-4 runners) and
one more date, with only arguments changed. Fix any hardcoded assumption (the event and state names, the playback-type field, the household column, the flat-export column names, the 6001-only WebView
rule) and record per-tenant mappings as parameters, never inline.

**Tests (no network):**
- `test_second_tenant_mapping_loaded` — a fixture for a second tenant's state vocabulary changes the result without code changes.
- `test_unknown_tenant_error` — an unresolved tenant stops with a clear message.

**Commit:** `feat(conviva-metrics): vsf technical second tenant`
