# Session presence funnel (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

This file is a starting spec and will be appended to as findings come in. Constraint for every task: no tenant code or id hardcoded; no network in tests; fixtures use placeholder ids.

---

## PF-1 — Pure library

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_presence.py` — pure functions plus small loaders (loaders take paths, logic functions take sets/dicts).
- `investigations/ctap-smvod/tests/test_session_presence.py` — covers the library.

**What to implement:**

1. Loaders that return the distinct non-blank `sessionId` set per source: Lightstep `smvod` (whole-day file or hourly `_NN_` parts, reusing the existing part-handling helper), Athena `session.csv`
   (`unified_sessions`) and `debug_states.csv`. Also return row counts so duplicates are visible (rows vs distinct). 1a. The Lightstep loader also returns the blank-`sessionId` rows (not just a
   count), with `http.status_code` when the column exists. This is the **first funnel item**: setup attempts (rows) = sessions created (distinct non-blank) + failed setups (blank). ZA 2026-10-24:
   4,449 = 4,443 + 6.
2. `funnel_stages(lightstep, unified, debug)` returns: distinct per source, in-`unified`, in-`debug`, in-both, in-either, in-neither, and the buckets `present_in_both`, `debug_not_unified`,
   `unified_not_debug` and `not_observed_in_athena`, plus the Athena-only set (in either Athena table, not in Lightstep). Reuse the set-diff and file-level logic of
   `compare_lightstep_athena_sessions.py` and `build_session_comparison_daily.py` (extract shared pure helpers; do not duplicate them).
3. `split_by_session_type(ids)` using `session_kind` from `scripts/lib/drm_funnel.py` (import, do not re-implement), so each stage is reported for `vod`, `linear` and `other`.
4. Type hints on all public functions; fail loudly on a missing `sessionId` column.

**Tests (no network, no real external services):**
- `test_stage_counts_and_overlaps` — a small fixture reproduces hand-computed counts, including the neither/Athena-only sets.
- `test_duplicate_and_blank_ids_counted_once` — duplicate rows and a blank `sessionId` do not inflate distinct counts.
- `test_split_by_session_type` — vod, linear and unknown prefixes land in the right bucket.
- `test_missing_session_id_column_raises` — a file without `sessionId` raises.
- `test_failed_setup_rows_counted_by_status` — blank-`sessionId` rows with 403 and 500 are reported as failed setups by status code; attempts = created + failed.
- `test_failed_setup_without_status_column` — an old export without `http.status_code` still counts the blank rows, with status "unknown".

**Commit:** `feat(ctap-smvod): add session presence funnel library`

---

## PF-2 — Report script

**Files to change / create:**
- `investigations/ctap-smvod/scripts/analyze_session_presence.py` — argparse (`--tenant`, `--date`, optional `--out-dir`); thin `main()` composing PF-1 and existing path helpers; calls
  `init_logging(...)`.
- `investigations/ctap-smvod/tests/test_analyze_session_presence.py`.

**What to implement:**

1. Write `output/<TENANT>/session-presence/<date>_session_presence.md` (stage table, overlap table, the per-`session_type` split) and `csv/<date>_session_presence.csv`, following the layout of
   `output/<TENANT>/drm-analysis/`. 1a. The report opens with a **setup stage** table (attempts, sessions created, failed setups split by `http.status_code`, and by `session_type` where the id
   exists), and `csv/<date>_session_presence_setup_failed.csv` lists the failed rows with `householdId`, `deviceId`, `session.clientIp`, `contentId`, `lightstep.trace_id`, `http.status_code`. Repeated
   failures by one household/device are counted as retries.
2. Write `csv/<date>_session_presence_missing.csv` listing Lightstep sessions not observed in Athena (in neither table), with `householdId`, `deviceId`, `contentId`, `start_time` when present in the
   merged file. Write `csv/<date>_session_presence_athena_only.csv` for sessions in Athena but not in the Lightstep export: `sessionId`, which Athena tables, first event time, and `near_part_boundary`
   (true when the first event lies within 2 minutes before a Lightstep export part boundary). The local debug-states file is Lightstep-scoped, so the Athena-only set needs the unscoped debug session
   list (`run_athena_debug_sessions.py`). Print the export time (`max(ingest_timestamp)`) in the report header so a later re-run's differences read as late ingestion.
3. Exit non-zero with a clear message if an input file is missing; never produce a partial report.

**Tests (no network, no real external services):**
- `test_report_written_for_fixture` — fixture inputs produce the markdown, CSV and missing-list files with expected rows.
- `test_missing_input_exits_nonzero` — a missing Athena export fails loudly.

**Commit:** `feat(ctap-smvod): add daily session presence report`

---

## PF-3 — Characterize missing sessions

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_presence.py` — add pure breakdown functions.
- `investigations/ctap-smvod/scripts/analyze_session_presence.py` — add the breakdown section to the report.
- Matching tests.

**What to implement:**

1. For the missing set, group by `Device Class`, `OS Family`, `Browser Name` and hour of day (UTC), reading the existing merged `setupsession` file; compare each rate against the observed set so
   over-representation is visible. First error code is **not** computed here: PF-8 owns the single first-error rule, and PF-3 reuses it once PF-8 exists (until then omit the column and say so). Also
   split by device level versus session level: sessions on devices that had an observed session that day versus devices with none (ZA 2026-10-24 baseline: 215 of 542 sessions versus 159 devices with
   every session unobserved).
2. State in the report when an enrichment source is absent for the date instead of silently omitting it.

**Tests:** one happy-path and one edge-case (empty missing set, missing enrichment file) per new function.

**Commit:** `feat(ctap-smvod): break down sessions missing downstream`

---

## PF-4 — Daily operation

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_pipeline.py` — add a step (flag `--skip-session-presence`) after the Athena outcome steps.
- `investigations/ctap-smvod/scripts/lib/session_presence.py` — `append_trend_row(...)` that upserts one row per tenant and date.
- `investigations/ctap-smvod/output/<TENANT>/session-presence/csv/session_presence_trend.csv` — generated output, not hand edited.
- Matching tests.

**What to implement:**

1. Upsert (not append) the daily row so a re-run replaces that date; columns: tenant, date, lightstep, unified, debug, both, neither, athena_only, unified_not_debug, `max_ingest_timestamp`, plus the
   VOD/linear split.
2. Run for every tenant the pipeline already iterates, with no per-tenant code.
3. Document the one-line daily command in `docs/usage.md`.
4. The trend row stays the Athena-presence counts; PF-8's pattern counts get their own `session_trace_patterns` file, so PF-4 needs no column change after PF-8.

**Tests:** `test_trend_upsert_replaces_same_day` and `test_trend_row_added_for_new_day`.

**Commit:** `feat(ctap-smvod): run session presence in daily pipeline`

---

## PF-5 — Validate and close out

**Files to change / create:**
- `investigations/ctap-smvod/docs/` — a short validation note; answers to the open questions in `prompt.md`.
- `investigations/ctap-smvod/docs/usage.md`, `CONTEXT.md` — current entries.

**What to implement:**

1. Run for ZA 2026-10-24 and confirm the baseline in `prompt.md` within the late-ingest tolerance: local-export snapshot 4,443 / 3,797 / 3,901 / 3,763 / 542 neither, 34 Athena-only, 138
   debug-not-unified (PF-6 split 137 present / 1 missing contentId); live 2026-10-26: 3,777 both / 137 / 529 neither. Record the export time next to the figures.
2. Run for one other ZA date and for ZM (which has linear) and confirm clean output and a sensible VOD/linear split.
3. Decide with a live Athena count whether local exports are complete; record the result.
4. Answer the open questions in `prompt.md`, including the expected-population finding from PF-7a and the headline "present in Athena" definition (decided: present = in both tables; record it in the
   report text). Run PF-5 after PF-8 so the whole report, including the trace matrix and charts, is validated.

**Tests:** run the existing ctap-smvod suite; it must be green.

**Commit:** `docs(ctap-smvod): record session presence validation`

---

## PF-6 — Daily debug-not-unified report (contentId category)

**Files to change / create:**
- `queries/athena/ctap-smvod-debug-session-content.sql` (catalog slug `ctap-smvod-debug-session-content`) — per `sessionId`, from `PLAYER_SESSION_EVENT` rows with `eventtype` in (`CREATE`,
  `CONTENT_UPDATE`): CREATE count, first CREATE time and `contentmetadata.contentid`; follow `docs/guides/query-catalog.md`.
- `investigations/ctap-smvod/scripts/run_athena_debug_session_content.py` — thin exporter to `data/athena/<TENANT>/<date>_debug_session_content.csv`.
- `investigations/ctap-smvod/scripts/lib/session_presence.py` — pure `debug_not_unified(debug_ids, unified_ids, content_by_session)` returning the set and its split.
- `investigations/ctap-smvod/scripts/analyze_session_presence.py` — add the section; matching tests.

**What to implement:**

1. For each tenant and day, take the sessions in debug states but not in `unified_sessions` and classify each: **contentId missing** (no CREATE/CONTENT_UPDATE with a non-empty
   `contentMetadata.contentId`) or **contentId present**. Also report the observed last state per session (CREATE only, buffering, destroyed) as a second breakdown.
2. Write `csv/<date>_debug_not_unified.csv` with one row per such `sessionId` (`sessionId`, `category`, `create_count`, `first_event`, `last_state`, `session_type`) so the list of affected sessions is
   available, and a count table in the markdown report.
3. Add the daily counts (total, contentId missing, contentId present) to the PF-4 trend row.
4. Tenant-agnostic: `--tenant` and `--date` arguments, Athena database and table from the tenant registry; no ids hardcoded.

**Baseline (ZA 2026-10-24, live Athena 2026-10-26):** 138 sessions = 137 contentId present + 1 contentId missing.

**Tests (no network, no real external services):**
- `test_debug_not_unified_split_by_content_id` — fixture with present, missing and blank contentId lands in the right category.
- `test_session_without_create_event_is_missing` — a session with no CREATE row is classed as contentId missing, not dropped.
- `test_no_debug_only_sessions_gives_empty_report` — empty set writes headers only.

**Commit:** `feat(ctap-smvod): report debug sessions missing from unified`

---

## PF-7a — Premise check (docs only)

Step 0 of the old PF-7, split out so it runs first. **Files:** `investigations/ctap-smvod/docs/session-trace/<tenant>_<date>_expected_population.md`.

Decide which sessions are *expected* in Athena: which clients/content emit debug telemetry (from the observed set), and whether the unobserved sessions look like a different population
(prefetch/probe, very short, non-instrumented clients, day-edge sessions). Record the expected population and its size; without it "not observed" cannot be read as a loss. Uses existing exports and
read-only live queries only; no code.

Evidence to start from (ZA 2026-10-24, local exports of 2026-10-26; associations, not causes): `playbackURL` packaging marks which content expects a licence — `/dash-wv-pr/` 4,217, `/hls-mp4-fp/` 190,
`/dash-clear/` 36, blank 6; none of the 36 clear sessions reach mdrmfe, as expected. `is_wv` (`scripts/lib/webview.py`) splits the attempts: 1,871 WebView attempts, 2 reach mdrmfe, 99.3% non-success;
1,906 non-WebView attempts, 1,744 reach mdrmfe, 38.9% non-success. The 1,996 `dash-wv-pr` attempts without an mdrmfe row are all non-success (VSF 1,933, EBVS 63). The WebView pattern repeats on
2026-10-21..23. Use packaging and `is_wv` to state which sessions are expected to request a licence before reading a missing mdrmfe row as a loss.

**Commit:** `docs(ctap-smvod): expected Athena population for sm-vod sessions`

---

## PF-7b — Lightstep forensics of sessions not observed in Athena

Mostly a manual analysis in Lightstep, supported by one catalogued query and one small helper. The set is the sessions in the Lightstep export that are in neither `unified_sessions` nor debug states
(the PF-2 "not observed" list; 542 in the local export, 529 live, ZA 2026-10-24). Runs after PF-2 and PF-6.

**Files to change / create:**
- `queries/lightstep/smvod-session-lifecycle.md` — UQL timeseries recipe (listed in `queries/lightstep/index.md`) that returns, per `sessionId` and for one household, the `sm-vod` operations (`POST`
  setup, `GET`, `DELETE` destroy) with `http.status_code`; follow `docs/guides/query-catalog.md`.
- `investigations/ctap-smvod/scripts/lib/session_presence.py` — pure `household_concentration(rows, key)` returning sessions per household/device/clientIp, sorted, with the share of the set.
- `investigations/ctap-smvod/docs/session-trace/<tenant>_<date>_missing_sessions_lifecycle.md` — dated findings doc.

**What to do:**

0. Premise check: done in PF-7a; link its findings doc here and do not repeat it.
1. Take the missing-downstream list from PF-2 (never a hardcoded id list) and tag each session with `householdId`, `deviceId` and `session.clientIp` from the Lightstep export.
2. Household concentration: count missing sessions per `householdId`, `deviceId` and `session.clientIp`, and compare each household's missing share with its total session count. State whether a small
   number of households (or one device model/IP range) accounts for a large part of the set, or whether it is spread out.
3. Lifecycle review in Lightstep with the catalogued query. For a sample first (about 30 sessions, then all if the pattern is clear), record per session: setup status code and duration, whether a
   `DELETE` exists and the gap from setup to `DELETE`, and any `404`/`5xx` on the session. Classify as **destroyed < 3 s**, **destroyed later**, **no destroy seen**, **setup error**. Time-series
   buckets are 60 s wide, so report the gap as a lower bound unless a span-level time is available.
4. Check the span coverage caveats: the Lightstep export window versus the Athena day (`timestamp_formatted`), and whether `sm-linear`, `ctap` or mDRM spans exist for the same session.
5. Cross-check the missing set against the Lightstep mDRM exports (`<date>_NN_mdrmfe.csv`, joined on `drmAuthToken.sessionId`; `mdrm-lrm` and `mdrm-cdm-*` via `fcid`) using the existing
   `scripts/lib/drm_exports.py` readers. Report, for the missing set and for the present set as a control, the share with an mdrmfe license (HTTP status), an LRM call and a CDM record. Content that is
   not DRM-protected never reaches mdrmfe, so split the missing set into **DRM chain present** and **no DRM trace**, and compare against the same split of the present set.
6. Record the counts per class, the household table and conclusions in the findings doc, and answer the matching open question in `prompt.md`.

**Baseline (ZA 2026-10-24, 5-session sample 2026-10-26):** setup HTTP 200 in about 30-40 ms for all 5; 2 had `DELETE` 204 at least 72 s later, 3 had no `DELETE` within 1.5 hours; none destroyed < 3 s.

**mDRM cross-check baseline (ZA 2026-10-24, 2026-10-26):** of the 542 missing sessions, 354 (65.3%) have an mdrmfe row (all HTTP 201) and 351 of those also have LRM and CDM records; 188 have no trace
in any source. Control: 1,743 of 3,763 observed sessions (46.3%) have mdrmfe, 1,711 with the full chain. The 138 debug-not-unified sessions: 50 (36.2%) have mdrmfe. A 201 shows a license was issued,
not that playback happened, and the rates are not like-for-like (DRM content only), so no cause is concluded: telemetry never sent versus an Athena ingestion gap stays open. The 188 may be clear
(non-DRM) content or very short sessions and need the lifecycle review in step 3. Device baseline: the 542 are on 266 devices; 215 sessions are on devices with an observed session that day, 159
devices have every session unobserved; top device 51 sessions (9%), top five households 21%.

**Tests (no network, no real external services):**
- `test_household_concentration_orders_by_count` — fixture with repeated households is sorted and carries the share.
- `test_household_concentration_blank_key_ignored` — rows with a blank key are not counted as a household.

**Commit:** `docs(ctap-smvod): lifecycle findings for sessions missing from Athena`


---

## PF-8 — Trace matrix and funnel charts (all sources)

Pulls PF-1/PF-3/PF-6/PF-7b and `session-error-model` together: one row per session, one pattern table, one chart set. Depends on PF-1 (id-set loaders), PF-7b (mDRM join) and PF-6 (contentId category),
plus EM-1/EM-2. The matrix is built here, not in PF-1, so PF-1 stays a three-source library. Naming: use `not_observed_in_athena`, never `dropped`, for the bucket and the report text.

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_trace_matrix.py` — pure functions: `build_matrix(...)`, `pattern_counts(matrix)`.
- `investigations/ctap-smvod/scripts/analyze_session_trace.py` — argparse (`--tenant`, `--date`), thin `main()`, `init_logging(...)`.
- `investigations/ctap-smvod/tests/test_session_trace_matrix.py`.
- Outputs under `output/<TENANT>/session-presence/`: `csv/<date>_session_trace_matrix.csv`, `csv/<date>_session_trace_patterns.csv`, `csv/<date>_session_trace_first_error.csv`, `charts/<date>_*.png`.

**Matrix columns (one row per distinct Lightstep `sessionId`):** `session_type`; `in_lightstep`, `in_mdrmfe`, `in_lrm`, `in_cdm`, `in_debug`, `in_unified` (booleans, LRM/CDM via `fcid` from mdrmfe);
`mdrmfe_status`; `pattern` (e.g. `mdrmfe+lrm+cdm|debug|-`); `bucket` (`present_in_both`, `debug_not_unified`, `unified_not_debug`, `not_observed_in_athena`; only `present_in_both` counts as present in
the headline); `has_content_id`; `householdId`, `deviceId`, `session.clientIp`, `contentId`; `first_error_code`, `first_error_source`, `all_error_codes`, `outcome`.

**First error and outcome:** defined once in `session-error-model/` (EM-1 `first_error`, EM-2 `classify_outcome`); this task imports them and does not redefine them. Rule in short: earliest by
datetime, all codes kept in `all_error_codes`, mDRM non-2xx before the first non-empty debug `errorcode`, then none observed; a failed setup is stage 0 and stays in the PF-2 setup-failed CSV. Sessions
not observed in Athena can only get an mDRM error, so "no error observed" is not "no error" for them; say so in the report. Cross-check against `<date>_error_eventdata.csv` and the existing
error-report CSV (`output/<T>/<date>_error_report_1xxx_6xxx.csv`) rather than recomputing 1xxx/6xxx logic.

**Charts (existing `src/lib/charts` only; no new dependency — `matplotlib-venn` and `upsetplot` are not installed):**
1. Stage funnel (`funnel_stages_chart.py`) in time order: Lightstep setup (with CTAP) → debug CREATE → mdrmfe → LRM → CDM → unified record, with the bucket split. Setup and CREATE are effectively
   simultaneous (median −0.07 s), and `unified_sessions` is derived from debug events, so it closes the funnel as a record, not a hop.
2. Stacked bar of the pattern table (`render_stacked_bar`), `green`/`red` reserved for healthy/failed.
3. A real Venn is only exact for 3 sets; use it only for Lightstep/debug/unified (3 sets). Anything with mDRM uses the pattern table and the stacked bar, which stay readable for 5-6 sources.

**Extra detail worth carrying (cheap, from existing files):** hour of `CREATE`/setup per bucket (outage-window test), `Device Class`/`OS Family`/browser, `contentId` present/missing, DRM type
(`drmAuthToken.drmType`), `ingest_timestamp` lag where present, household count per bucket, `playback_packaging` (from `playbackURL`) and `is_wv`. Hop timestamps, latencies and the furthest hop are
added on top of this matrix by SL-2 (`session-lifecycle-report/`), not here.

**Tests (no network):** `test_pattern_counts_match_hand_fixture`, `test_first_error_and_outcome_come_from_error_model`, `test_blank_session_id_excluded`, `test_missing_source_file_raises`.

**Commit:** `feat(ctap-smvod): add session trace matrix and funnel charts`
