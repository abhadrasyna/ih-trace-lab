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
2. `funnel_stages(lightstep, unified, debug)` returns: distinct per source, in-`unified`, in-`debug`, in-both, in-either, in-neither, and the Athena-only and debug-not-unified sets.
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
2. Write `csv/<date>_session_presence_missing.csv` listing Lightstep sessions found in neither Athena table, with `householdId`, `deviceId`, `contentId`, `start_time` when present in the merged file.
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

1. For the missing set, group by `Device Class`, `OS Family`, `Browser Name` and first error code, reading the existing merged `setupsession` file and (when present) the error and mDRM exports;
   compare each rate against the present set so over-representation is visible.
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

1. Upsert (not append) the daily row so a re-run replaces that date; columns: tenant, date, lightstep, unified, debug, both, neither, athena_only, plus the VOD/linear split.
2. Run for every tenant the pipeline already iterates, with no per-tenant code.
3. Document the one-line daily command in `docs/usage.md`.

**Tests:** `test_trend_upsert_replaces_same_day` and `test_trend_row_added_for_new_day`.

**Commit:** `feat(ctap-smvod): run session presence in daily pipeline`

---

## PF-5 — Validate and close out

**Files to change / create:**
- `investigations/ctap-smvod/docs/` — a short validation note; answers to the open questions in `prompt.md`.
- `investigations/ctap-smvod/docs/usage.md`, `CONTEXT.md` — current entries.

**What to implement:**

1. Run for ZA 2026-10-24 and confirm the baseline in `prompt.md` (4,443 / 3,797 / 3,901 / 3,763 / 542 neither, 34 Athena-only, 138 debug-not-unified).
2. Run for one other ZA date and for ZM (which has linear) and confirm clean output and a sensible VOD/linear split.
3. Decide with a live Athena count whether local exports are complete; record the result.

**Tests:** run the existing ctap-smvod suite; it must be green.

**Commit:** `docs(ctap-smvod): record session presence validation`
