# Monthly error code pipeline — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to the backlog/session-log file.

All scripts are thin: pure logic functions plus a `main()` with `argparse`, `init_logging()`, and shared code from `src/lib/` (Athena adapter, monthly CSV store, tenant registry). Before writing any
script, check `SCRIPTS.md` and the FCT-6 registry for an existing equivalent.

---

## MEC-0 — September adoption-session-report CSV per OpCo

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/run_month_adoption_session_report.py` — thin orchestrator.
- `investigations/mtn-monthly-error-code-analysis/tests/test_run_month_adoption_session_report.py`
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — add the entry and the first run-order row.

**What to implement:**

1. Reuse `src/pipelines/aws_access_cli/scripts/run_adoption_session_report.py` (`main(argv)` → `common.run_adoption_cli`, metrics `SESSION_METRICS`); do not copy its SQL. This report reads
   `unified_<id>.unified_sessions`, not the `_ccl_debug_events_sept26` tables.
2. Only a single `--date` run upserts into the month file via `MonthlyCsvStore` (a `--start-date/--end-date` range does not), so the orchestrator loops every date in the month and every OpCo, calling
   `main(["--date", D, "--tenant", T, "--output-dir", "investigations/mtn-monthly-error-code-analysis/output", "--skip-auth-check"])`. Run SSO once up front; isolate per-date/per-OpCo failures and
   exit non-zero if any failed. Result: `output/<OPCO>/daily/2026-09_adoption-session-report.csv` (the output dir is resolved against the repo root).
3. Args: `--month YYYY-MM` (required), `--opco` (repeatable, default all four), `--force`, `--dry-run` (print the date x OpCo plan, run nothing).
4. Open decision to confirm before coding: the pipeline names South Africa `ZA` (`src/pipelines/aws_access_cli/tenants.py`) while `config/tenants.yaml` and these docs say `SA`. Default: use the
   pipeline's `ZA` so the folder matches the existing `output/ZA/daily/` files; document the mapping in `usage.md`.
5. The data must have settled: ZA session counts were still rising two days after the first run (7 Oct vs 9 Oct), so September (closed) is safe; for a current month, wait 2-3 days after month end.

**Tests (no network, no real external services):**
- `test_plan_covers_every_date_and_opco` — a 30-day month x 4 OpCos yields 120 calls, with the expected `--date`/`--tenant`/`--output-dir` argv.
- `test_failure_is_isolated_and_exit_nonzero` — one failing call does not stop the rest, and the exit code is non-zero.
- `test_bad_month_fails` — an invalid month raises a clear error.

**Commit:** `feat(mec): add September adoption-session-report orchestrator`

---

## MEC-1 — Define error-code source and count grain; add catalog query

**Files to change / create:**
- `queries/athena/mtn-monthly-error-code-counts.sql` — month-parameterized error-code count query.
- `investigations/mtn-monthly-error-code-analysis/docs/error-code-source.md` — chosen table, field, count grain, OpCo database naming.
- catalog entry per `docs/guides/query-catalog.md`.

**What to implement:**

1. The September 2026 source databases are given in `prompt.md` "Data sources" (`<athena_tenant_id>_ccl_debug_events_sept26`; the unified session DB `unified_<id>` is unchanged). Still confirm with
   the user which table and field in them hold the error code, and whether a row counts distinct sessions, households, or raw events.
2. Adapt the closest prior art (`ctap-smvod-error-eventdata.sql` first, `aws-access-cli_shaka_error_counts.sql` second) with a whole-month predicate so counts are not double-counted across days; reuse
   `ctap-smvod`'s `render_query` and `resolve_tenant_context(code, table_suffix="sept26")` instead of new plumbing.
3. Document the decisions in `error-code-source.md`.

**Tests (no network, no real external services):**
- `test_query_renders_for_month` — the catalog template renders with OpCo and month parameters.
- `test_query_rejects_bad_month` — an invalid month raises a clear error.

**Commit:** `feat(mec): add monthly error-code catalog query`

---

## MEC-2 — Per-OpCo monthly Athena pull script

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/pull_monthly_error_codes.py`
- `investigations/mtn-monthly-error-code-analysis/tests/test_pull_monthly_error_codes.py`

**What to implement:**

1. Args: `--month YYYY-MM`, `--opco <CODE>` (default: all in `config/tenants.yaml`).
2. Thin orchestrator: per OpCo, call `resolve_tenant_context(code, table_suffix=...)`, then reuse `run_athena_error_eventdata.build_query`/`run_athena_query` (from `ctap-smvod/scripts/lib/runtime.py`)
   with the MEC-1 query; isolate per-OpCo failures and exit non-zero if any failed. Do not re-implement Athena polling.
3. Write the raw result to `data/athena/<OPCO>/YYYY-MM/`.

**Tests (no network, no real external services):**
- `test_pull_writes_per_opco_files` — a fake adapter result lands in the expected path.
- `test_pull_unknown_opco_fails` — an unknown OpCo exits with a message naming the registry.

**Commit:** `feat(mec): add per-OpCo monthly error-code pull`

---

## MEC-3 — Cross-OpCo aggregation into the monthly report

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/build_monthly_report.py`
- `investigations/mtn-monthly-error-code-analysis/tests/test_build_monthly_report.py`

**What to implement:**

1. Read the pulled data for a month and write per-OpCo and all-OpCo CSVs to `output/<OPCO>/` and `output/ALL/`, reusing `flatten_error_eventdata`/`summarize_error_eventdata` logic and
   `src/lib/csv_io/monthly_store.py` where they fit.
2. Include error code, count, share of total, and rank.

**Tests (no network, no real external services):**
- `test_report_totals_match_input` — the all-OpCo total equals the sum of the per-OpCo totals.
- `test_report_missing_month_fails` — a month with no pulled data fails loudly.

**Commit:** `feat(mec): add monthly error-code report`

---

## MEC-4 — Month-over-month comparison

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/scripts/compare_months.py`
- `investigations/mtn-monthly-error-code-analysis/tests/test_compare_months.py`

**What to implement:**

1. Args: `--from-month`, `--to-month`, optional `--opco`.
2. Diff the two reports: absolute and percentage change, and new or disappeared codes.

**Tests (no network, no real external services):**
- `test_compare_flags_new_and_gone_codes` — new and removed codes are labelled.
- `test_compare_same_month_fails` — identical months raise an error.

**Commit:** `feat(mec): add month-over-month error-code diff`

---

## MEC-5 — Finalize runbook, usage.md, SCRIPTS.md

**Files to change / create:**
- `investigations/mtn-monthly-error-code-analysis/docs/usage.md` — fill the run-order table and one entry per script.
- `SCRIPTS.md` — register every new script.
- `CONTEXT.md` — update "What Exists".

**What to implement:**

1. Replace the "(TBD)" rows in `usage.md` with the real scripts, args, inputs, outputs and examples.
2. Add the first dated findings doc, `docs/YYYY-MM-all-findings.md`, from a real run.

**Tests:** none (docs only); verify the documented commands run.

**Commit:** `docs(mec): finalize monthly error-code runbook`
