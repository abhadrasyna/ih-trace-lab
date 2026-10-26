# Session lifecycle report (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

Constraint for every task: no tenant code or id hardcoded; no network in tests; fixtures use placeholder ids; prototypes start in `scratch/` per `scratch/SCRATCH.md` and move to
`investigations/ctap-smvod/scripts/` only once proven; outputs go under `output/<TENANT>/session-lifecycle/` (`csv/`, `charts/`).

---

## SL-1 — Export completeness check

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/export_completeness.py` — pure functions over already-loaded rows: `kind_summary(kind, rows, parts)` and `completeness_status(summaries)`.
- `investigations/ctap-smvod/scripts/check_export_completeness.py` — argparse (`--tenant`, `--date`), thin `main()`, `init_logging(...)`; reads with the existing `scripts/lib/drm_exports.py` readers.
- `investigations/ctap-smvod/tests/test_export_completeness.py`.
- Output: `output/<TENANT>/session-lifecycle/csv/<date>_export_completeness.csv`.

**What to implement:**

1. Per export kind (smvod, smvod-ts, ctap, mdrmfe, LRM, CDM per DRM type): rows, parts, time window (fcId prefix for mDRM, span time where present), and whether any part reaches the known cap
   (`smvod-ts` ~499, CDM ~1,000; caps are parameters, not literals in logic).
2. Consistency checks: mdrmfe rows ≥ LRM rows; for a tenant with `shared_project: true`, exactly one value of the `disambiguation_attribute` (`busUnitId`) per file, else fail loudly.
3. Status per tenant/date: `complete`, `partial` (a window gap or a cap hit) or `unusable` (a hop's window covers too little of the day for rates); the reason is written next to it. A tenant without
   `mdrm_tenant_id` gets `not_applicable` for mDRM kinds.
4. Print a short manual export checklist: which kinds or parts are missing or need splitting.

**Tests:** `test_cap_hit_marks_partial`, `test_window_gap_marks_partial`, `test_lrm_more_than_mdrmfe_flagged`, `test_two_bus_units_in_shared_project_raises`, `test_no_mdrm_tenant_is_not_applicable`.

**Baseline (local exports of 2026-10-26):** ZA 2026-10-24 `smvod-ts` cap hit and Widevine CDM ends 22:56 (partial); ZA 2026-10-21 LRM/CDM cover 18:42–23:49 (mDRM unusable); GH 2026-10-24 mdrmfe starts
12:01 and LRM rows exceed mdrmfe (partial).

**Commit:** `feat(ctap-smvod): add export completeness check`

---

## SL-2 — Lifecycle model

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/session_lifecycle.py` — pure functions: `build_lifecycle(matrix, outcomes, timings, cohorts)`, `furthest_hop(row)`, `hop_latencies(rows)`, `path_counts(rows)`.
- `investigations/ctap-smvod/scripts/analyze_session_lifecycle.py` — argparse (`--tenant`, `--date`), thin `main()`.
- `investigations/ctap-smvod/tests/test_session_lifecycle.py`.
- Outputs: `csv/<date>_session_lifecycle.csv` (one row per session), `csv/<date>_lifecycle_paths.csv`, `csv/<date>_lifecycle_latency.csv`.

**What to implement:**

1. Rows are the union of Lightstep sessions (PF-8 matrix) and EM-2 attempts, with `in_lightstep` and `is_attempt`, so attempts missing from Lightstep and Lightstep sessions that are not attempts both
   stay visible.
2. Hop order: setup (CTAP same trace) ≈ debug CREATE → mdrmfe → LRM → CDM → playback → end (`../README.md`). `furthest_hop` is the last hop reached in that order; `path` is the PF-8 pattern.
3. Timestamps: setup from `smvod-ts` (null where the cap removed it), CREATE and first error and last event from debug states, licence time from the fcId prefix (named `license_t_fcid_proxy`).
   Latencies are written as p5/p50/p95 with n per interval and outcome.
4. Cohort columns: `session_type`, `is_wv` (`scripts/lib/webview.py`), `playback_packaging`, DRM type, CDM security level, licence rows per session. Outcome and first error are imported from
   `session-error-model/`.
5. Linear sessions keep their own `session_type`; for a tenant whose export has no sm-linear setup yet, `abr-linear-` sessions seen only in mDRM are counted as `linear_not_covered`, not as losses.

**Tests:** `test_furthest_hop_order`, `test_attempt_without_lightstep_kept`, `test_capped_setup_time_is_null_not_zero`, `test_latency_percentiles_hand_fixture`, `test_linear_without_setup_not_a_loss`.

**Baseline:** the furthest-hop and timing figures in `prompt.md` (ZA 2026-10-24) within the late-ingest tolerance.

**Commit:** `feat(ctap-smvod): add session lifecycle model`

---

## SL-3 — Daily summary report

**Files to change / create:**
- `investigations/ctap-smvod/scripts/render_session_lifecycle_report.py` — reads the SL-1, SL-2, EM-4 and PF-8 CSVs only (no recomputation) and writes
  `output/<TENANT>/session-lifecycle/<date>_summary.md` and its charts.
- `investigations/ctap-smvod/scripts/lib/lifecycle_report_text.py` — pure functions that turn CSV rows into sentences and tables.
- `investigations/ctap-smvod/tests/test_lifecycle_report_text.py`, `tests/test_render_session_lifecycle_report.py`.

**What to implement:**

1. Header: tenant, UTC date, completeness status with reasons, every source file with its export time, and the minimum n used (default 30).
2. Sections, each with its chart and a generated explanation (every number comes from a CSV): journey funnel with outcome split (`funnel_stages_chart.render_stages_chart`); furthest hop × outcome
   (100% `render_stacked_bar`); paths table; hop latency percentiles (`render_bar`); cohorts by outcome — WebView, packaging, DRM type, security level (`render_stacked_bar`, associations only); hour ×
   outcome (stacked bar per UTC hour, no heatmap); a Mermaid flow block of the main paths (text, no rendering).
3. Embed the EM-4 charts and link the existing `drm-analysis` reports for the date when present, but not their error-codes chart.
4. Rates below the minimum n show the count and "n too small". Partial days show counts but no rates for the affected hops. Linear sections appear only where `session_type` exists, otherwise a "linear
   not covered" banner.
5. Follow `docs/guides/chart-guidelines.md`: green/red for success/failure only, null buckets muted, export time in each footnote.

**Tests:** `test_sentence_uses_csv_numbers`, `test_small_n_suppresses_rate`, `test_partial_day_hides_rates`, `test_error_codes_chart_not_linked`, `test_charts_write_nonempty_pngs`.

**Commit:** `feat(ctap-smvod): add daily session lifecycle report`

---

## SL-4 — Daily operation

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_pipeline.py` — a step after the PF-4 session-presence step (flag `--skip-session-lifecycle`) that runs SL-1, SL-2 and SL-3 for every tenant the pipeline
  iterates.
- Reuse `append_trend_row(...)` from PF-4 (`scripts/lib/session_presence.py`) to upsert `output/<TENANT>/session-lifecycle/csv/session_lifecycle_trend.csv`.
- `investigations/ctap-smvod/docs/usage.md` — the one-line daily command, the D+2 run timing (late ingest) and the export checklist.
- Matching tests.

**What to implement:**

1. Trend columns: tenant, date, completeness status, attempts, Lightstep sessions, furthest-hop counts, outcome counts, licence-reach share, WebView share, VOD/linear split, export times.
2. Upsert, not append: a re-run replaces that date.
3. No per-tenant code: a new tenant (NG) is picked up once its exports exist; mDRM hops are omitted where `mdrm_tenant_id` is absent.

**Tests:** `test_trend_upsert_replaces_same_day`, `test_tenant_without_mdrm_runs`.

**Commit:** `feat(ctap-smvod): run session lifecycle in daily pipeline`

---

## SL-5 — Flow and timeline prototypes (exploratory)

**Files to change / create:** `scratch/` only, registered per `scratch/SCRATCH.md`.

**What to implement:** a sankey of tenant → WebView/non-WebView → licence requested or not → outcome, and a per-session timeline for a sample of sessions per outcome (setup, CREATE, licence, first
error, end). Use the SL-2 CSVs. Promoting either helper into `src/lib/charts` needs separate approval and its own task.

**Tests:** none (scratch).

**Commit:** `chore(scratch): prototype lifecycle sankey and timeline`

---

## SL-6 — Validate and close out

**Files to change / create:**
- `investigations/ctap-smvod/docs/` — a validation note per tenant; an NG onboarding checklist (Lightstep project, Athena db, no mDRM tenant yet, which report sections are omitted).
- `CONTEXT.md` — "What Exists" entry.

**What to implement:**

1. Run ZA 2026-10-21..24 and confirm 2026-10-24 against `prompt.md`; 2026-10-21 shows mDRM `unusable`.
2. After LC-2, run GH and ZM for one re-exported day each; confirm the linear split and check whether the outcome rules hold for linear (open question in `session-error-model/prompt.md`).
3. Grep scripts and tests for hardcoded tenant codes or ids; there must be none.

**Tests:** run the ctap-smvod test suite; it must be green.

**Commit:** `docs(ctap-smvod): record session lifecycle validation`
