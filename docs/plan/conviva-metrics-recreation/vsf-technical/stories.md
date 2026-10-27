# Video Start Failures Technical — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

Tests: scratch work is exempt from the test gate until graduation (CMR-VSFT-5); verify by running on the saved data and recording the output. Confirm scope and plan with the user before creating or
editing anything (project Steps 2-3).

**Build rule (user, 2026-10-27):** the scratch POC only validates that the metric is possible. Every formal script and helper is built while working the tasks, as tested code, not left for the end and
not run through MCP. Code specific to this story lives in `investigations/conviva-metrics/`, common code in `src/lib/`. Before writing anything new, read the existing runners and helpers and reuse or
enhance them: the raw export, session loader, `day_bounds()`, line renderer, breakdown helper and report writer all come from `../concurrent-plays/` (CMR-CP-2, CMR-CP-6). Do not copy them.

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
8. Story shape: five tasks as in `../video-startup-time/`; option B is not built.

---

## CMR-VSFT-1 — Settle the open definition points and the report content

**Files:** this story's `prompt.md` (definition section), the approved report `2026-10-24_ZA_vsf-technical-error-summary-optionA.md` if its sections change, and the `../discussion-prompt.md`
Discussion log.

**What to settle with the user (discussion, no code):**

1. The business-error list (MEC-27): who owns it, where it will live (a config file per tenant is the proposal), and the rule for a session with both business and technical codes (the POC says any
   business code makes it VSF-B).
2. Errors after `DESTROY` or after the start window: drop them as the POC does, or add Conviva's 90 s late-error window.
3. Equal timestamps (error before `PLAYING`) and a session that errors, then plays: confirm the error does not count if `PLAYING` follows.
4. Bandwidth: confirm Shaka `estimatedbandwidth`, the band edges (1, 3, 10 Mbps) and the "no data" row; whether `navigatorconnection.downlink` should be a second measure.
5. Which codes get a detail table (6001, 3016, 1003, E31012 today): a fixed list, or every code above a share threshold.
6. Chart: the 5-minute series, and whether the PNG is committed beside the report (the POC copied it into the story folder; plan folders should hold only `.md`) or stays in the gitignored `output/`
   with a link.
7. The error-codes table: whether to add a total row and a peak bucket column, and whether the full household id stays out of the report.
8. A Conviva VSF-T figure for ZA on 2026-10-24 to compare against, the tolerance that counts as a match, and the Conviva reporting timezone.

**Commit:** `docs(conviva-metrics): cmr-vsft-1`

---

## CMR-VSFT-2 — Explain the number

**Files:** a new `scratch/<date>_conviva-vsf-technical_gap_probe.py` (registry stub per `scratch/SCRATCH.md`) and a findings note in the report or `prompt.md`.

**What to implement:**

1. Attempts: 3,954 sessions with `CREATE` in `debug_all_events.csv` against 3,901 in the attempts POC's `debug_states.csv`. List the sessions that differ and say which side matches Conviva.
2. The 10 sessions the POC counts as VSF and `outcome_first_debug.csv` does not: their events, and which rule (equal timestamps, error then play, late error) explains each.
3. The 16 VSF-T sessions with no row in the flat error export, and the 58 sessions whose first error is not 6001, 3016, 1003 or E31012: why, and which codes they carry.
4. Multi-code sessions: how many carry more than one code, which pairs, and how the "any code" table and the "first error" detail tables differ per code (for example 6001: 1,898 against 1,887).
5. The 6001 repeat households: the households with the most 6001 sessions, whether the sessions are retries inside minutes or spread over the day, and whether one device type drives them.
6. State, per category, whether it belongs in the Conviva definition.

**Commit:** `docs(conviva-metrics): cmr-vsft-2`

---

## CMR-VSFT-3 — Prove the POC generalises

**Files:** the three POC scripts, and a short note on any per-tenant state-name or column differences.

**What to implement:** run for one more tenant with Athena debug events and error eventdata (GH or ZM; check what exists locally first, otherwise fetch with the CMR-CP-2 runner and, for the eventdata,
the pull that CMR-VSFT-4 formalises) and one more date, with only arguments changed. Fix any hardcoded assumption (the `CREATE`, `PLAYING`, `DESTROY` and `PLAYER_ERROR` names, the `abr-vod-`
playback-type prefix, the household column, the flat-export column names, the 6001-only WebView rule) and record per-tenant mappings as parameters, never inline.

**Commit:** `docs(conviva-metrics): cmr-vsft-3`

---

## CMR-VSFT-4 — Close the data gaps

**Files:** a scratch probe and findings note; the POC scripts and report; an Athena query in the catalog and a runner with a saved export for the flat error eventdata.

**What to implement:**

1. Business-error list: record what the user supplies in CMR-VSFT-1, or document the blocker. The classification stays configurable either way.
2. The flat error export: today `flatten_error_eventdata.py` in `investigations/ctap-smvod/scripts/` produces it from `error_eventdata.csv` by hand. Give it a catalogued query, a runner with `--date`,
   `--tenant`, `--dry-run` and `--force`, a saved export, offline tests and a registry update, wrapping (not editing) the flattener.
3. Bandwidth for 6001: its events carry no Shaka stats, so check whether `navigatorconnection.downlink` (always present) can fill the bandwidth columns, or whether the "no data" row stays.
4. Device and playback type: reuse the CMR-CP-5 sources (parsed user agent, DRM device type, raw `contenttype`) instead of finding them again; replace the session-id prefix guess for playback type
   with the raw field; record any gap as a blocker.
5. Fetch only what is missing, with a catalogued query, and save it for reuse.

**Commit:** `docs(conviva-metrics): cmr-vsft-4`

---

## CMR-VSFT-5 — Formal recreation: graduate code and data (needs its own go-ahead)

**Files:** a VSF-T script, a pure module and a report writer with tests in `investigations/conviva-metrics/scripts/`; Athena catalog entries only for inputs CMR-VSFT-4 added; `SCRIPTS.md`; retire the
three scratch copies per `scratch/SCRATCH.md`. The line renderer, loader, breakdown helper and report writer are the shared ones from CMR-CP-6.

**Design map (from `docs/refactor/design-principles.md`, `code-deduplication-and-taxonomy.md`, `python-hygiene-and-automation.md` and `docs/guides/functional-code-taxonomy.md`):** metric rules stay in
`investigations/conviva-metrics/`, mechanisms used by more than one metric go to `src/lib/`. Each piece is a pure function; `main()` only parses arguments and wires.

| POC piece | Formal home | Change |
|---|---|---|
| `read_sessions` (the timeseries POC) | the CMR-CP-6 loader over the raw export plus `build_sessions(rows)` | reuse; do not copy |
| `"PLAYER_SESSION_EVENT"`, `"CREATE"`, `"DESTROY"`, `"PLAYING"`, `PLAYER_ERROR` literals | the per-tenant state-vocabulary dataclass from CMR-CP-6 | no module constants |
| `business` set, `interval`, `top` loose arguments | a frozen `VsfRules` dataclass (business codes, interval, top) passed in | typed, one parameter object |
| `create_time`, `start_failure` | pure `find_attempt` and `find_start_failure(events, vocab)` returning a typed `StartFailure`; a Strategy `Callable` classifies VSF-T or VSF-B | SRP, OCP |
| `bucket`, `series_points` | take the day length and interval as parameters; empty buckets are gaps | no magic numbers |
| `top_content`, `playback_type`, `table` | the shared breakdown helper and table renderer from CMR-CP-6; playback type from the raw field (CMR-VSFT-4) | shared |
| `code_rows` (the error-codes-table POC) | pure `error_code_rows(failures, households, attempts, top)` returning a typed row list | logic apart from rendering |
| `band`, `BANDS` (the error-bandwidth POC) | a `BandwidthBands` value in `VsfRules` and a pure `band(value, bands)`; NaN and negative are "no data" | data, not code |
| first-error pick and detail grouping (error-bandwidth POC) | pure `group_first_errors(flat_rows)` and `detail_table(rows, columns)`; per-code column spec | extension by data |
| the p50 and p90 expressions | one tested `percentile()` helper in `src/lib/` (nearest rank, shared with the VST story) | shared |
| `load_poc` importlib loader | removed; the pure module is imported normally | hygiene |
| `render_report` | the `src/lib/report_render/` writer behind a `Protocol`; the option A sections are the template | shared |
| `render_line` | the `src/lib/charts/` line renderer (a count axis, gaps for empty buckets) | shared |
| `SystemExit`, `print`, the `outcome_first_debug.csv` overlap check | domain errors, `setup_logging()`; the overlap check a documented reconciliation or dropped | hygiene |
| `DATA` path and the `/tmp` flat file | `src/lib/paths` and the saved flat export from CMR-VSFT-4 | no hardcoded paths |

Extensibility: a different business list, interval or band set is a different `VsfRules` value, and a new code detail column is an entry in the per-code column spec, not a new branch (OCP). The pure
module must not import the report or chart code (DIP).

**What to implement:** only after CMR-VSFT-1 to CMR-VSFT-4 are done, CMR-CP-6 is done and the user agrees. Tenant, date, interval, business codes, bands and state mapping are arguments; the script
runs on demand and in a daily run reading the saved exports and writes the report to the story folder as `<date>_<tenant>_vsf-technical-report.md` in the option A layout.

**Tests (no network, no real external services):**
- `test_failure_is_error_before_first_playing` — a `PLAYER_ERROR` at 10:00:03 before `PLAYING` at 10:00:10 is a start failure bucketed at 10:00:03.
- `test_error_after_playing_is_not_failure` — an error after `PLAYING` does not count.
- `test_error_after_destroy_not_failure` — an error after `DESTROY` does not count.
- `test_equal_timestamp_error_first` — shuffled rows with equal timestamps for `PLAYER_ERROR` and `PLAYING` give the same result, the error winning.
- `test_blank_error_code_counted` — a failure with a blank code is counted under `(blank)`.
- `test_business_code_makes_vsfb` — a session with any business code is VSF-B, the rest VSF-T; with an empty list everything is VSF-T.
- `test_attempts_only_with_create_on_date` — a session without `CREATE` on the date is not an attempt.
- `test_summary_rate_is_failures_over_attempts` — the share equals failures divided by attempts.
- `test_empty_bucket_is_gap` — a bucket with no failures has no value on the chart series.
- `test_series_reconciles_with_summary` — the bucket counts add up to the VSF-T total.
- `test_error_code_rows_multi_code` — a session with two codes counts under both; the rows do not have to add up to the total.
- `test_households_distinct_and_blank_excluded` — impacted households are distinct ids; sessions with no household are counted in sessions but not in households or in sessions per household.
- `test_sessions_per_household_uses_household_sessions` — three sessions, one without a household, over two households give 1.0, not 1.5.
- `test_first_and_last_seen_are_utc` — the first and last failure times come from the failure times, in UTC.
- `test_group_first_errors_picks_earliest` — a session with two error rows is grouped under the earlier code.
- `test_pipeline_status_spellings_merged` — the three 3016 spellings become one group.
- `test_bandwidth_band_edges` — 0.99, 1.0, 3.0 and 10.0 Mbps fall into the right bands; NaN, negative and blank are "no data".
- `test_percentile_nearest_rank` — p90 of ten values is the ninth, never the maximum; a group of one or two is never below the median.
- `test_detail_table_has_spacer_columns` — the rendered table has a blank column between each pair and the same cell count in every row.
- `test_webview_column_only_for_6001` — other codes' detail tables do not carry the WebView pair.
- `test_no_failures_error` — no VSF-T sessions on the date raises a clear error; no household in the session export raises a clear error.
- `test_report_content_reconciles` — each breakdown table plus its Unresolved row equals the VSF-T total.

**Commit:** `feat(conviva-metrics): graduate vsf technical poc`
