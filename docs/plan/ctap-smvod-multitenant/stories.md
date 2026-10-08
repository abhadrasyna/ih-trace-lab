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

## MT-8 — Docs and close

**Files to change / create:** `investigations/ctap-smvod/docs/usage.md` (new layout, `--tenant`, per-tenant export rule incl. `busUnitId` filter, how to add a tenant), `CONTEXT.md` "What Exists".

**What to implement:** document; run the full ctap-smvod test suite and `code-review-checklist.md`. **Commit:** `docs(ctap-smvod): document multi-tenant usage`
