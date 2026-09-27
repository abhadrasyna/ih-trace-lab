# Tenant registry — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.
> Full implementation rules live in `PYTHON_DESIGN.md` and `AGENTS.md`.
> After each task: set `SHA:` on the task line + tick the box, update the story status
> summary, add one line to your backlog/session-log file.

**Confirmed tenant data (source of truth for TR-1/TR-2 — do not re-derive, re-verify, or invent additional tenants):**

| Opco | Go ID | Lightstep Project | Region | Shared project? | Disambiguation attribute | Matisse Project ID | Matisse Client Tenant ID | Athena Tenant ID | Athena profile/region |
|---|---|---|---|---|---|---|---|---|---|
| South Africa | `iye9omdf` | `mcs-go-prod-iye9omdf-eu` | EU | No | n/a (`syna.tenant` = Go ID) | `1z5vo5g2` | `rxviifsu` | `e6auj7k7` | `clarissa-insights-product`, `eu-central-1` |
| Nigeria | `q95itlcu` | `mcs-go-prod-q95itlcu-eu` | EU | No | n/a (`syna.tenant` = Go ID) | `4l5rt293` | `y54b5mqr` | `jsxgloje` | `clarissa-insights-product`, `eu-central-1` |
| Zambia | `dtunf6yo` | `mcs-go-prod-mtn-1-eu` | EU | **Yes** | `sessionInfo.busUnitId = dtunf6yo` (`syna.tenant` = `mtn-1`, not opco-specific) | `lsok8ywy` | `p0yxunm4` | `a7vli5h8` | `clarissa-insights-product`, `eu-central-1` |
| Ghana | `apbyfj9d` | `mcs-go-prod-mtn-1-eu` | EU | **Yes** | `sessionInfo.busUnitId = apbyfj9d` (`syna.tenant` = `mtn-1`, not opco-specific) | `0800cgn3` | `hkq8wgfy` | `is1aldzq` | `clarissa-insights-product`, `eu-central-1` |

Athena `database` for each opco is `unified_<athena_tenant_id>` (confirmed pattern, matches `aws-access-cli/scripts/athena_runner/tenants.py`).

---

## TR-1 — Scratch probe: tenant resolution + real Lightstep MCP round-trip

**Files to change / create:**
- `scratch/<today>_tenant_lightstep_probe.py` — quick POC, relaxed bar per `scratch/SCRATCH.md` (no tests, no type-hint enforcement required)
- `scratch/<today>_tenant_lightstep_probe_findings.md` — records what was queried and whether the result matched the expected opco

**What to implement:**

1. In the scratch script, hardcode (do not import anything — this is a throwaway probe) a minimal dict for exactly 2 opcos: South Africa (`iye9omdf`, dedicated project) and Ghana (`apbyfj9d`, shared
   project `mcs-go-prod-mtn-1-eu`), using the confirmed data table above.
2. Write one small function that, given an opco's Go ID, returns `{"project": ..., "region": ..., "filter": {...} | None}` — `filter` is `None` for a dedicated project, `{"sessionInfo.busUnitId": <go_id>}`
   for a shared one.
3. Run the function for both opcos and print the resolved output.
4. **Stop here and state to the human exactly which Lightstep MCP tool/query you intend to run next** (per `AGENTS.md`'s hard gate — this applies regardless of it being a "probe"). Suggested: a
   `query_spans` or `list_services` call scoped to `mcs-go-prod-iye9omdf-eu` (no filter) and a second one scoped to `mcs-go-prod-mtn-1-eu` with `sessionInfo.busUnitId = apbyfj9d`, using a short recent
   time window. Wait for explicit go-ahead before invoking either.
5. Run the approved MCP call(s). Record in the findings doc: the exact query issued, a short excerpt of the result, and whether it visibly corresponds to the expected opco (e.g. service names/tags
   consistent with Ghana rather than Zambia or SA).

**Tests:** none — scratch scripts are exempt (`scratch/SCRATCH.md`).

**Commit:** `docs(tenant-registry): record TR-1 scratch probe findings`
(the scratch script itself is not held to `src/` discipline but is still committed under `scratch/`, per this project's convention that scratch work is tracked, not gitignored, unless `SCRATCH.md`
says otherwise for a specific artifact type)

---

## TR-2 — `config/tenants.yaml`: canonical MTN tenant config

**Files to change / create:**
- `config/tenants.yaml` — canonical config, all 4 opcos from the table above
- `config/README.md` (or a top comment block in the YAML itself if a separate README is overkill for one file) — one paragraph: what this file is, that it is the *only* place tenant data lives, and
  the naming convention (`database = unified_<athena_tenant_id>`)

**What to implement:**

1. Only proceed if TR-1's findings confirm the resolution logic produced a query that returned opco-appropriate results. If TR-1 found a mismatch, stop and flag it — do not write the config with
   unconfirmed values.
2. Structure `config/tenants.yaml` as a top-level `opcos:` list (not a dict keyed by one ID type — this must be look-up-agnostic; the loader in TR-3 builds whichever indexes it needs). Each entry
   carries every column from the table above, plus a `code` field (`SA`, `NG`, `ZM`, `GH`) for human-facing CLI use.
3. Add a short header comment stating this file is the single source of truth — no tenant literal should exist in `src/`, `scripts/`, `docs/guides/tenant-resolution.md`, or `AGENTS.md` after this
   task; those may only reference this file.

**Tests:** none (pure data file) — but `TR-6` will assert the file parses and matches the expected shape once the loader exists.

**Commit:** `feat(tenant-registry): add canonical config/tenants.yaml`

---

## TR-3 — `src/tenant_registry/`: `TenantConfig`/`TenantRegistry`/`QueryTarget` implementers

**Files to change / create:**
- `src/tenant_registry/__init__.py`
- `src/tenant_registry/models.py` — frozen `TenantConfig` dataclass mirroring `config/tenants.yaml`'s fields (type-hinted, per `AGENTS.md` Python conventions)
- `src/tenant_registry/registry.py` — `TenantRegistry`: loads `config/tenants.yaml` (path injectable via `__init__`, default `config/tenants.yaml` relative to repo root — Dependency Inversion, so tests
  can pass a fixture path instead), builds lookup indexes by every ID type + `code`, `get(identifier) -> TenantConfig` raising `KeyError` with the list of valid ids on a miss (mirror the proven
  `aws-access-cli/scripts/athena_runner/tenants.py` pattern — do not reinvent the error shape)
- `src/tenant_registry/query_targets.py` — a `QueryTarget` `Protocol` with one method, `build_context(tenant: TenantConfig) -> dict`, plus 3 implementers: `LightstepGoQueryTarget`,
  `MatisseQueryTarget`, `AthenaQueryTarget`

**Before any code:** read `PYTHON_DESIGN.md`'s SOLID triggers section. The `QueryTarget` split exists specifically to avoid an `if system == ...: elif ...` branch in one method (the OCP trigger) —
do not collapse the 3 implementers back into a single function with a `system` parameter.

**What to implement:**

1. `TenantConfig`: one field per column in TR-2's table, plus `code`. No behavior — pure data (SRP: behavior lives in `QueryTarget` implementers, not here).
2. `TenantRegistry.get(identifier)`: identifier can be a Go ID, Matisse Project ID, Matisse Client Tenant ID, Athena Tenant ID, or `code` — try all indexes, raise `KeyError` on a miss listing every
   registered Go ID (the most human-recognizable id) as the "available" list.
3. `LightstepGoQueryTarget.build_context(tenant)`: returns `{"project": tenant.lightstep_project, "region": tenant.lightstep_region, "filter": {"sessionInfo.busUnitId": tenant.go_id} if
   tenant.shared_project else None}`. If `tenant.shared_project` is `True` and, for any reason, `tenant.go_id` is falsy, raise `ValueError` — this is the enforcement point protecting against a
   silent broad query on a shared project.
4. `MatisseQueryTarget.build_context(tenant)`: returns `{"project_id": tenant.matisse_project_id, "client_tenant_id": tenant.matisse_client_tenant_id}`.
5. `AthenaQueryTarget.build_context(tenant)`: returns `{"database": f"unified_{tenant.athena_tenant_id}", "profile": tenant.athena_profile, "region": tenant.athena_region}`.

**Tests:** written in TR-6, not here (this task is implementation only per the task split — if trivial to co-locate, still keep the TR-6 checkbox separate since it tracks test-completeness
explicitly per this story's `tasks.md`).

**Commit:** `feat(tenant-registry): add TenantRegistry and QueryTarget implementers`

---

## TR-4 — `scripts/resolve_tenant.py` CLI wrapper

**Files to change / create:**
- `scripts/resolve_tenant.py`

**What to implement:**

1. `argparse` CLI: `--system {lightstep_go,matisse,athena}` and `--tenant <any known id>` (no hardcoded default — matches this project's argparse-not-hardcoded convention).
2. Loads `TenantRegistry` (default config path), resolves `--tenant` via `.get()`, dispatches to the matching `QueryTarget` implementer (a small `{"lightstep_go": LightstepGoQueryTarget(), ...}`
   dict literal in `main()` is acceptable here — this is the CLI's one allowed dispatch point, not a repeated decision method elsewhere).
3. On success: print the `build_context` result as a single line of JSON to stdout, exit 0.
4. On any `KeyError`/`ValueError` from the registry or query target: print the exception message to stderr, exit 1. No stack trace noise — this output is meant to be read by a human or by this
   assistant deciding whether to proceed, so keep it terse.
5. Uses `setup_logging()` from `logs/setup_logging.py` only if the script logs anything beyond its final stdout/stderr line (per `AGENTS.md`); avoid adding logging noise that would pollute the
   single-line JSON contract on success.

**Tests:** CLI smoke test in TR-6 (success case + failure case, asserting exit code and stdout/stderr shape).

**Commit:** `feat(tenant-registry): add resolve_tenant.py CLI`

---

## TR-5 — `docs/guides/tenant-resolution.md` + `AGENTS.md` pointer

**Files to change / create:**
- `docs/guides/tenant-resolution.md`
- `AGENTS.md` — one line added at the existing `<!-- INSERT: investigations -->` marker under "Domain conventions"

**What to implement:**

1. `docs/guides/tenant-resolution.md` states the protocol: before invoking any Lightstep/Matisse/Athena MCP tool for a named opco, run
   `python scripts/resolve_tenant.py --system <system> --tenant <id>` via the `bash` tool first; use its JSON output to build the MCP call; if it exits non-zero, stop and ask rather than guessing or
   falling back to a hardcoded value. Never inline tenant IDs/projects in this doc — always point at `config/tenants.yaml` and the CLI as the source of truth.
2. Also document the shared-project case explicitly (Zambia/Ghana both resolve to `mcs-go-prod-mtn-1-eu`; the CLI's `filter` output is what disambiguates them) so a future reader understands *why*
   the CLI step exists, not just that it's mandatory.
3. `AGENTS.md` gets exactly one line at `<!-- INSERT: investigations -->`: a pointer sentence to `docs/guides/tenant-resolution.md`, phrased as a hard requirement consistent with this project's
   existing tool-invocation gate style. No tenant data, no opco list, no ID values in `AGENTS.md` itself.

**Tests:** none (docs-only) — `docs-plan-story-structure`/checkbox pre-commit hooks still apply to this story's own plan folder, not to this task's output.

**Commit:** `docs(tenant-registry): add tenant-resolution protocol guide`

---

## TR-6 — Tests for registry, query targets, and CLI

**Files to change / create:**
- `tests/tenant_registry/test_registry.py`
- `tests/tenant_registry/test_query_targets.py`
- `tests/tenant_registry/test_resolve_tenant_cli.py`
- `tests/tenant_registry/__init__.py` (and any missing intermediate `__init__.py` per `AGENTS.md`'s package convention)
- `tests/fixtures/tenants_test.yaml` — a small fixture config (2–3 entries) so registry tests don't depend on the real `config/tenants.yaml` changing shape

**What to implement (per `AGENTS.md` Step 4 — one happy-path + one edge/error test per public function, no network):**

- `test_registry.py`: `test_get_by_each_id_type_returns_correct_tenant`, `test_get_unknown_identifier_raises_key_error_listing_available_ids`.
- `test_query_targets.py`: `test_lightstep_go_dedicated_project_has_no_filter`, `test_lightstep_go_shared_project_includes_bus_unit_id_filter`, `test_matisse_and_athena_build_context_happy_path`,
  `test_lightstep_go_shared_project_missing_go_id_raises_value_error` (the enforcement case).
- `test_resolve_tenant_cli.py`: `test_cli_success_prints_json_and_exits_zero`, `test_cli_unknown_tenant_exits_nonzero_with_message` (invoke via `subprocess`/direct `main()` call — no real MCP/network).

**Commit:** `test(tenant-registry): cover registry, query targets, and CLI`
