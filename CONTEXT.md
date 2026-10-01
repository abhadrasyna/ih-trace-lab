# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `.github/hooks/session-context.json` — a native Copilot CLI `sessionStart` hook (not a git hook) that auto-injects a short reminder into every new/resumed session: read `CONTEXT.md`, state
  `CONTEXT.md ✓`, confirm scope when files aren't named, and state a plan + wait for go-ahead before non-trivial changes. Added to cut the highest-recurrence rows in `suggestions.md`
  (`wait-for-explicit-go-ahead-before-editing`, `state-context-md-checkmark-explicitly`, etc.) at the source instead of only catching them after the fact in `session-close`. Injects a short pointer,
  not the full `AGENTS.md`/`CONTEXT.md` text, to avoid adding token cost every session.
- **Copilot Memory is enabled** (`/memory on`, confirmed 2026-10-01) — a per-user CLI account setting, not a repo file; there is nothing under this repo to look for. Intended to reduce the
  `avoid-broad-filesystem-finds`/`avoid-mid-session-rereads` rows in `suggestions.md` by letting the CLI recall repo-structure facts across sessions instead of re-discovering them each time.
- `docs/plan/tenant-registry/` — story complete: `config/tenants.yaml` is now the canonical MTN tenant-identifier config for all 4 confirmed opcos (Go ID, Matisse Project/Client Tenant ID, Athena
  Tenant ID, Lightstep project/region, shared-project disambiguation attribute); `src/tenant_registry/` loads it and resolves per-system query contexts (`TenantRegistry`/`QueryTarget`); this assistant
  must consult it (via `scripts/resolve_tenant.py` or the loader directly) before any Lightstep/Matisse/Athena MCP call, per `docs/guides/tenant-resolution.md`'s CLI-first protocol. TR-1's scratch
  probe was confirmed against real, human-reviewed Lightstep MCP data (dedicated SA project + shared Ghana project disambiguated by `busUnitId`) before any production code was written.
- `docs/plan/query-catalog/` — story complete: `queries/athena/` + `queries/lightstep/` now provide a deduplicated, parameterized-template query catalog harvested from `github_copilot`'s 3
  `QUERY_CATALOG.md` files plus `lightstep-query-templates.md`; the Athena/Lightstep harvest scripts are in `scripts/dev/`, the query indexes/templates live under `queries/`, the query workflow guide
  lives at `docs/guides/query-catalog.md`, and the ported (not yet run) Athena DDL-cache tooling plus `knowledge/README.md` live under `knowledge/` / `scripts/athena/`.
- `docs/plan/project-taxonomy/` — story complete: `docs/guides/project-taxonomy.md` now defines the four categories, folder skeletons, prior-art checklist, pipeline cron-cutover procedure, and PT-7
  data/knowledge conventions; `config/data_paths.yaml` is the path-template source of truth; `scripts/dev/check_project_taxonomy.py` audits unclassified top-level dirs; and
  `.github/skills/investigation-doc-sync/SKILL.md` defines the deferred cross-session case-doc sync workflow. `structure.md` remains the canonical target-tree reference for this story and
  `functional-code-taxonomy`.
- `docs/plan/functional-code-taxonomy/` — story complete: `docs/guides/functional-code-taxonomy.md` now maps the six shared `src/lib/*` modules, states the shared-vs-specific test, records the
  `query-catalog` boundary, and documents the delegated cross-project duplicate-check. `src/lib/{athena,report_render,har}/protocols.py` and `src/lib/paths/{protocols.py,config.py}` now provide the
  shared Protocol/path-resolution seams, with tests; `scripts/dev/generate_code_registry.py` inventories reusable code outside `scratch/`. Sibling to `project-taxonomy` (categories vs. shared code)
  and `query-catalog` (SQL text vs. execution code).
- `docs/plan/scratch-script-registry/` — story complete: root `SCRIPTS.md` is now generated from the live `scripts/` + `scratch/` tree via `scripts/dev/generate_scripts_registry.py`;
  `scripts/dev/promote_scratch_scripts.py` provides manual promotion with registry refresh; `scratch/SCRATCH.md`, `AGENTS.md`, and the repo-local `.github/skills/session-close/SKILL.md` enforce the
  delegated duplicate-check and close-out regeneration workflow; `tests/dev/` covers both CLIs.
- `docs/plan/reference-knowledge-harvest/` — story complete through RKH-17: `knowledge/` now contains the harvested VOD asset mapping/pipeline references, MTN SA Lightstep tag/query references,
  Applause Athena/CSV gotchas, adoption playback-outcome gap notes, CTAP-SM-VOD playback/CDN methodology docs, MTN/TIM Play tenant+DRM references, the 3 root knowledge ports, and the SRE Jira project
  reference. The story remains extensible — future `github_copilot/*` folders would reopen it by appending new `RKH-N` tasks rather than creating a new story.
- `docs/plan/src-lib-migration/` — epic: real, tested implementations of `functional-code-taxonomy`'s six `src/lib/*` modules (`auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`),
  ported/refactored from `github_copilot` (read-only reference), one story per module. `athena-lib-integration` is the exception — it wires in `/Users/abhadra/myWork/myOffice/athena-mcp-server` (an
  already-independent, tested repo with the shared `athena_runner` execution stack) as a git submodule and adapts to it, rather than re-porting a fifth copy of that logic.
  `auth`/`csv_io`/`curl_to_python` additionally define their own `Protocol`s here, deferred by `functional-code-taxonomy` FCT-2. Now unblocked by `functional-code-taxonomy`; see
  `docs/plan/src-lib-migration/athena-lib-integration/tasks.md` for the first unchecked task (ALI-1).
- `docs/plan/pipeline-migration/` — epic: ports `aws-access-cli` (→ `src/pipelines/aws-access-cli/`, pipeline category, incl. PT-6 cron-cutover) and `ctap-smvod-session-report` (→
  `investigations/ctap-smvod/`, recurring-campaign category, incl. manual-Lightstep-step relocation) from `github_copilot` (read-only reference), replacing their duplicated executor/auth/SQL/output
  logic with `src/lib/*`, `query-catalog`, and `project-taxonomy` PT-7's ISO-prefix path convention respectively. Blocked on `project-taxonomy` PT-1/2/6/7, `src-lib-migration`, and `query-catalog`
  landing first. Not yet implemented — see `docs/plan/pipeline-migration/aws-access-cli-pipeline-migration/tasks.md` for the first unchecked task (AAM-1).
- `docs/plan/reference-code-gap-migration/` — **epic** (promoted from a single story by its own GAP-1 task, 2026-09-30): ports the 10 `github_copilot` projects (~166 Python files) that neither
  `pipeline-migration` nor `src-lib-migration` cover, into 10 sub-stories tiered by effort/blocking (`README.md`'s decision log) — Tier 1 cheap (`applause-investigation-migration`,
  `astro-events-household-investigation-migration`, `shaka-6001-sa-investigation-migration`, `root-scripts-tool-migration`), Tier 2 medium (`vod-asset-ingestion-investigation-migration`,
  `mtn-zm-device-investigation-migration`, `mtn-network-traffic-tool-migration`, `root-investigations-migration`), Tier 3 blocked on two newly-promoted `src/lib/*` modules
  (`vod-playback-timing-probe-tool-migration` needs `mpd`, `smarttv-mtntv-tool-migration` needs `crypto_signing` — both modules to be built by `src-lib-migration`, not this epic). GAP-1 also flagged a
  correction to `project-taxonomy/structure.md`/`stories.md`: `vod-asset-ingestion-mapping` recategorized from `experiments/` to `investigations/vod-asset-ingestion/` (recurring campaign, per its own
  README); a second, similar tension for `vod-playback-timing-probe` (audit suggests "tool", `structure.md` still examples it under `experiments/`) was flagged but deliberately left unresolved for a
  future `project-taxonomy` session. `oasis-athena-mcp` was checked and confirmed not a gap (superseded by the `athena-mcp-server` submodule). Root `prompt.md` is now a pure router (no session-start
  protocol of its own) — each of the 10 sub-stories has its own `prompt.md`/`tasks.md`/`stories.md` and first unchecked task (all currently their own `<PREFIX>-1` audit task). Not yet implemented
  beyond GAP-1 — see `README.md`'s Stories table for which sub-story to pick up next. **2026-10-01:** cross-cutting constraint added requiring any sub-story that ports a CSV/report-writing script to
  adopt `PathResolver`'s naming helpers (`format_snapshot_filename`/`format_range_filename`/`format_rollup_filename`), not just its directory resolver — confirmed by source read that
  `shaka-6001-sa-error-analysis`, `mtn-zm-session-device-investigation`, `astro-events-household-report`, and `vod-playback-timing-probe` each still hardcode their own ad hoc output-path logic today;
  mirrors `pipeline-migration` AAM-4's already-designed task shape.

- `docs/plan/reference-folder-diagrams/` — story complete: `scripts/reference_diagram/` now supports per-project internal-import flowcharts, and `docs/reference-diagrams/` now indexes 12 folder-level
  Mermaid pages (generated flowcharts plus hand-authored convergence/orchestration/state diagrams) covering every in-scope `github_copilot` migration folder except deliberately-excluded
  `oasis-athena-mcp`; the set makes `reference-code-gap-migration`'s tiering and its `src/lib/mpd/` / `src/lib/crypto_signing/` promotion decisions visible, not just prose.
- `docs/plan/flow-correlation-id-logging/` — story complete (design-only): defines the project's FCID (flow-correlation-id) convention — one id per run, minted once at each consumer's entry point,
  propagated via a `contextvars.ContextVar` (no manual parameter-threading through `src/lib/*` adapter methods), auto-injected into every log line via a `logging.Filter`. `stories.md` carries a
  sequence diagram (one Athena query inside one pipeline run) and a component diagram (FCID flowing through `src/lib/*` into all three migration epics' consumers); no `src/lib/logging/` module or code
  exists yet — that is deferred to a follow-up story once a real consumer (first candidate: `athena-lib-integration` ALI-2) needs it. Coordination notes were added to `src-lib-migration`,
  `pipeline-migration`, and `reference-code-gap-migration`'s `README.md`s pointing here. Cross-process FCID propagation (subprocess/cron boundaries) is explicitly out of scope, left open for later.
- `docs/plan/pre-implementation-design-review/` — story complete: a SOLID/clean-code/extensibility design review of all 18 not-yet-started stories across `src-lib-migration`, `pipeline-migration`, and
  `reference-code-gap-migration`, run before any of them starts producing code. `spec.md` is the full findings table. One low-risk finding was fixed directly: a blocking method-name/signature mismatch
  between `src/lib/athena/protocols.py`'s `AthenaClient` and `athena-lib-integration/stories.md`'s own ALI-2 class diagram, which would have failed that story's own task gate. A second finding (a
  design-time-diagram-discipline parity constraint for `reference-code-gap-migration/README.md`) was applied, then reverted 2026-10-01 at the requester's instruction as a self-introduced extension
  outside their stated review criteria — `spec.md`'s finding #11 row records this. **2026-10-01 follow-up: all 6 originally-flagged judgment calls resolved** (`spec.md`'s "Flagged for human decision"
  section now records each resolution) — (a) `src-lib-migration/README.md` gained a standardized two-assertion DIP-enforcement test pattern, applied to `athena-lib-integration`'s ALI-3 and
  `auth-lib-migration`'s AUM-3; (b) `report-render-lib-migration` gained a new `RRM-3` Factory Method task (`src/lib/report_render/factory.py`) selecting a writer by shape key, renumbering the prior
  RRM-3/RRM-4 to RRM-4/RRM-5; (c) `curl-to-python-lib-migration`'s CPM-1 framing corrected to cite its real confirmed consumer (a HAR-driven manual timing/latency investigation workflow), replacing
  the prior "no-citation/speculative" framing; (d) the task-authoring SRP nit (finding #7) was left as-is, no split; (e) `ctap-smvod-investigation-migration`'s CSM-2 class diagram fixed to show
  `RunPipeline` delegating to explicit `MergeScript`/`AnalyzeScript` collaborators instead of modeling their logic as inline methods; (f) `athena-lib-integration` gained two new tasks, `ALI-4` (audit
  existing `athena_runner` batch/cache support) and `ALI-5` (`src/lib/athena/batch.py` + `cache.py` — bounded-concurrency `BatchQueryRunner` + `InMemoryTtlCache`, both DIP-compliant), with the prior
  ALI-4 (doc pointers) renumbered to `ALI-6`. **2026-10-01, same-day extended review pass (user-requested, 8 dimensions + progressive query scoping):** grounded in a direct read of the
  `athena-mcp-server` submodule's source (not speculation) — found and fixed a real defect: ALI-5's just-committed batch design did not satisfy `flow-correlation-id-logging`'s own stated
  `contextvars`/`ThreadPoolExecutor` caveat (FCID would have silently vanished inside worker threads); ALI-5 now captures `copy_context()` on the calling thread before submitting work. ALI-2 gained a
  mirrored `src/lib/athena/exceptions.py` hierarchy (never leaking `athena_runner.exceptions.*`) and throttling retry/backoff (confirmed missing upstream in `query_executor.py`); ALI-5 now reuses
  `athena_runner.config.RunConfig.max_concurrency` (confirmed reserved-but-unconsumed upstream) instead of a redundant new constructor arg, and pre-builds all `AthenaClient` instances sequentially
  before starting its thread pool (`AwsClientFactory`'s shared-`boto3.Session` construction is not documented safe for concurrent calls). A new `ALI-6` task (`src/lib/athena/progressive.py`) adds a
  progressive scope-widening query runner — narrow scope first, widen only if insufficient, combine rows across every scope actually run — per the user's own 9th review requirement; the prior ALI-6
  (doc pointers) renumbered to `ALI-7`. `flow-correlation-id-logging/stories.md` gained a PII/secrets redaction rule (log `sql_fingerprint`, not raw SQL; allow-list param keys).
  `src-lib-migration/README.md`'s cross-cutting constraints gained 5 generalized rules beyond the `athena`-specific instances: exception-hierarchy-per-module, config-loading consistency (cite
  `src/lib/paths/config.py`'s `PathConfig`), import-cycle/dependency-direction (one-directional `src/lib/*` graph, future `test_no_import_cycles.py`), shared test-fixture dedup (future
  `tests/lib/conftest.py`), and the packaging/import-path gap (no root `pyproject.toml`/`conftest.py` yet — `python -m pytest`-from-repo-root is the only reason `from src.lib...` imports currently
  work; flagged as an open item for `pipeline-migration`'s first integration task).

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
