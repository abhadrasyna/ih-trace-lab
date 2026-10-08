# CTAP/SM-VOD multi-tenant support — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Follow `docs/refactor/` (see `prompt.md`) and run its `code-review-checklist.md` before each commit. After
> each task: set `SHA:` on the task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

---

## MT-1 — Audit tenant-specific hardcoding

**Files to change / create:**
- `docs/plan/ctap-smvod-multitenant/stories.md` — append an "MT-1 findings" section (file:line, what is hardcoded, which later task fixes it).

**What to implement:**

1. Grep `investigations/ctap-smvod/{scripts,scripts/lib}` and the Athena SQL templates under `queries/athena/` for tenant ids, project ids, profiles, regions, `data/`/`output/` path literals.
2. Run `python scripts/resolve_tenant.py` for ZM and SA to confirm the registry values this story will consume.
3. Check `SCRIPTS.md`/`src/lib` for existing tenant-aware helpers before designing new ones.

**Tests:** none (read-only). **Commit:** `docs(ctap-smvod-multitenant): record MT-1 audit findings`

---

## MT-2 — Tenant-namespaced paths

**Files to change / create:**
- `config/data_paths.yaml` — add tenant-scoped templates for investigation data and output.
- `investigations/ctap-smvod/scripts/lib/runtime.py` — `snapshot_output_path`/`range_output_path`/`rollup_output_path` and input-path helpers take a tenant code.
- `investigations/ctap-smvod/tests/test_output_paths.py` — per-tenant path cases.

**What to implement:** one place builds `output/<TENANT>/…`, `data/lightstep/<TENANT>/…`, `data/athena/<TENANT>/…`; scripts call the helpers instead of building paths.

**Tests:** `test_paths_are_tenant_scoped`; `test_missing_tenant_raises`. **Commit:** `feat(ctap-smvod): namespace input/output paths by tenant`

---

## MT-3 — Tenant context and discovery

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/tenant_context.py` — resolve a tenant code via `TenantRegistry` into a frozen context (athena tenant id, profile, region, Lightstep project, disambiguation
  attribute); `discover_tenants(date)` lists tenant folders holding that date's Lightstep files.
- `run_athena_playback_outcome.py`, `run_athena_debug_events.py` — take the injected context; SQL parameterised with the Athena tenant id.
- `investigations/ctap-smvod/tests/` — new tests.

**Tests:** `test_discovery_finds_only_tenants_with_date_files`; `test_unknown_tenant_fails_with_expected_path`; `test_context_values_come_from_registry`. **Commit:** `feat(ctap-smvod): resolve tenant
context and discover inputs`

---

## MT-4 — Pipeline orchestration

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_pipeline.py` — no flag: run every discovered tenant for `--date`; `--tenant <code>`: one tenant. Each tenant runs the existing steps with its context. A
  tenant's failure is recorded, the others continue, a per-tenant summary prints at the end, exit non-zero if any failed. `--dry-run` prints per-tenant commands. Tenant code is logged on every run
  line.
- `investigations/ctap-smvod/tests/test_run_pipeline.py` — extend.

**Tests:** `test_default_runs_all_discovered_tenants`; `test_tenant_flag_runs_only_that_tenant`; `test_one_failure_does_not_stop_others_and_exits_nonzero`; `test_no_tenant_input_fails_loudly`.
**Commit:** `feat(ctap-smvod): run pipeline per tenant`

---

## MT-5 — Shared-project guard

**Files to change / create:**
- `investigations/ctap-smvod/scripts/merge_ctap_smvod_csv.py` (or a lib helper it calls) — when the tenant's `disambiguation_attribute` is set, require that column and reject rows whose value differs.
- `investigations/ctap-smvod/tests/` — guard tests.

**Tests:** `test_foreign_busunitid_rows_fail_merge`; `test_dedicated_project_tenant_skips_guard`. **Commit:** `feat(ctap-smvod): guard shared Lightstep projects by busUnitId`

---

## MT-6 — Migrate existing SA files

**Files to change / create:** `git mv` existing `data/lightstep/*`, `data/athena/*`, `output/*` under the SA tenant folder (code per `config/tenants.yaml`); fix references in docs.

**What to implement:** move only; no content edits. Re-run one SA date with `--dry-run` and, if inputs allow, a real run to confirm identical outputs. **Tests:** existing suite green. **Commit:**
`refactor(ctap-smvod): move SA data under tenant folder`

---

## MT-7 — Zambia pilot

**What to implement:** user exports one Zambia date from Lightstep (filtered on `sessionInfo.busUnitId`) into `data/lightstep/ZM/`; run `run_pipeline.py --date <d> --tenant ZM`; reconcile row counts
and compare error-code distribution sanity vs Ghana. Record results in a dated doc under `investigations/ctap-smvod/docs/`. **Commit:** `docs(ctap-smvod): record Zambia pilot results`

---

## MT-8 — `is_wv` column in the error report

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/webview.py` — move `_is_wv` here as a public helper (keyed on `raw_user_agent`, falling back to the parsed `Platform` column, `; wv` token).
- `investigations/ctap-smvod/scripts/analyze_webview_devices.py`, `analyze_wv_device_cross_date_success.py` — import the shared helper; no behaviour change.
- `investigations/ctap-smvod/scripts/extract_error_report_1xxx_6xxx.py` — add `is_wv` to `DEFAULT_COLUMNS` and each row; flows into the per-date CSV and the range `.xlsx`.
- `investigations/ctap-smvod/tests/test_extract_error_report.py`, `tests/test_analysis_helpers.py` — coverage.

**What to implement:** the source is `<date>_setupsession_with_outcome.csv`, whose `raw_user_agent` already comes from `<date>_ctap.csv` (`http.user_agent`), so the ctap files are not re-read. `is_wv`
is `true` when the UA contains the `; wv` token, `false` when a UA is present without it, and blank when no UA is available, so a missing UA is never reported as non-wv.

**Tests:** `test_wv_user_agent_marked_true`; `test_non_wv_user_agent_marked_false`; `test_missing_user_agent_is_blank_not_false`; `test_is_wv_column_in_xlsx`. **Commit:** `feat(ctap-smvod): add is_wv
to 1xxx/6xxx error report`

---

## MT-9 — Rerun dates with empty user agent

**What to implement:** 2026-10-02's `setupsession_with_outcome.csv` has an empty `raw_user_agent` for all 40 error rows (output predates the column). After MT-6, rerun the merge for each affected date
and tenant (`--skip-step3 --skip-step4` if the Athena files are cached), regenerate the error-report CSVs and the 01–06 Oct xlsx, and confirm no blank `is_wv` remains. **Commit:** `data(ctap-smvod):
refresh error reports with is_wv`

---

## MT-10 — Docs and close

**Files to change / create:** `investigations/ctap-smvod/docs/usage.md` (new layout, `--tenant`, per-tenant export rule incl. `busUnitId` filter, how to add a tenant), `CONTEXT.md` "What Exists".

**What to implement:** document; run the full ctap-smvod test suite and `code-review-checklist.md`. **Commit:** `docs(ctap-smvod): document multi-tenant usage`

---

## MT-1 findings (audit, 2026-10-08)

Registry values (`scripts/resolve_tenant.py`): SA Athena `unified_e6auj7k7`, Lightstep `mcs-go-prod-iye9omdf-eu` (no filter); ZM Athena `unified_a7vli5h8`, Lightstep `mcs-go-prod-mtn-1-eu` with
`sessionInfo.busUnitId = dtunf6yo`. Both share profile `clarissa-insights-product` and region `eu-central-1`. No existing tenant-aware helper in `src/lib`; `src/tenant_registry` is the one to consume.

| File:line | Hardcode | Fixed by |
|---|---|---|
| `queries/athena/ctap-smvod-debug-states.sql:2,19` | table `e6auj7k7_ccl_debug_events`; prefix is the SA tenant id, so `{{database}}` alone is not enough | MT-3 (add a table param from registry) |
| `queries/athena/ctap-smvod-debug-completeness.sql:2,16` | literal `unified_e6auj7k7` and `e6auj7k7_ccl_debug_events` | MT-3 (parameterise or confirm unused by the pipeline) |
| `scripts/run_athena_debug_events.py:104` | `--database` default `unified_e6auj7k7` | MT-3 |
| `scripts/run_athena_playback_outcome.py:65` | `--database` default `unified_e6auj7k7` | MT-3 |
| `scripts/lib/runtime.py:16,20` | `DEFAULT_PROFILE`, `_DEFAULT_REGION` (same for ZM/SA; keep as fallback, prefer registry) | MT-3 |
| `scripts/run_athena_debug_events.py:54,90`, `run_athena_playback_outcome.py:46` | `data/athena` and `output` roots built by hand | MT-2 |
| `scripts/run_pipeline.py:82-83,100-102,122,126,141,164` | `LIGHTSTEP_DIR`/`ATHENA_DIR` and input filenames, no tenant | MT-2, MT-3, MT-4 |
| `scripts/merge_ctap_smvod_csv.py:259` | `--input-dir` default `data/lightstep`; no `busUnitId` check | MT-2, MT-5 |
| `scripts/merge_session_outcome.py:368` | default input dir `data/athena` | MT-2 |
| `scripts/lib/runtime.py:48-76` | `investigation_output_dir`/`snapshot_/range_/rollup_output_path` take no tenant | MT-2 |
| `config/data_paths.yaml:15-16` | `investigation_data`/`investigation_output` templates have no tenant segment | MT-2 |
| `analyze_*`, `build_*`, `extract_*`, `filter_error_code_report.py`, `correlate_cdn_ips.py` | `output/` defaults and rollup globs (`build_mtn_summary.py:46`) | MT-2 (rollups per tenant) |
| `scripts/lightstep_ctap_smvod_join.py:30,286` | `--project` required, example is SA project (docs only, not hardcoded) | none |
| `scripts/analyze_webview_devices.py:68` | `_is_wv` defined locally | MT-8 |

Not tenant-specific: `mtn_escalation*` names in `correlate_cdn_ips.py`/`build_mtn_summary.py` refer to the MTN operator group (both tenants), not SA.

**Risk to flag for MT-3:** the table-name prefix finding means `ctap-smvod-debug-states.sql` would silently query the SA table for ZM if only `--database` changed. Confirm the ZM table is
`a7vli5h8_ccl_debug_events` (e.g. via the registry/`knowledge/` DDL or `SHOW TABLES`) before MT-3.
