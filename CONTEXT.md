# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `docs/plan/tenant-registry/` — story: canonical MTN tenant-identifier config (Go ID, Matisse Project/Client Tenant ID, Athena Tenant ID, Lightstep project/region, shared-project disambiguation) + a
  resolver this assistant must consult before any Lightstep/Matisse/Athena MCP call. Not yet implemented — see its `tasks.md` for the first unchecked task (TR-1).
- `docs/plan/query-catalog/` — story: `queries/athena/` + `queries/lightstep/` deduplicated, parameterized-template query catalog (harvested from `github_copilot`'s 3 `QUERY_CATALOG.md` files +
  `lightstep-query-templates.md`), plus a ported (not yet run) Athena DDL-cache under `knowledge/`. Not yet implemented — see its `tasks.md` for the first unchecked task (QC-1). Its DDL-cache task
  (QC-4) depends on `tenant-registry` landing first for any live Athena discovery.
- `docs/plan/project-taxonomy/` — story: classifies work into 4 categories (pipeline, investigation — bounded case or recurring campaign, tool, experiment; a fifth "continuous investigation" category
  was dropped after concluding a git submodule boundary solves no use case here — recurring campaigns are plain folders, differing from bounded cases only via PT-7's config-driven `data/`+`output/`
  path templates and an optional `RETENTION.md` marker), per-category folder skeleton (Rule A: no double `investigations/` wrap; Rule B: campaign slug + flat ID-prefixed cases), a new-work checklist
  covering both new folders and new scripts, and a pipeline cron-cutover procedure (for `aws-access-cli`-style live crontab migrations) — informed by a `github_copilot` audit (read-only reference);
  also specs (PT-8, deferred until PT-2/PT-7 land) an `investigation-doc-sync` skill, modeled on `session-close`, that syncs case docs from `session_store_sql` via a case-scoped, content-filtered,
  cursor-in-deliverable mechanism rather than a manual mid-investigation dump. `structure.md` in this story's folder is the canonical target-tree reference both this story and
  `functional-code-taxonomy` point to. Not yet implemented — see its `tasks.md` for the first unchecked task (PT-1).
- `docs/plan/functional-code-taxonomy/` — story: target `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/` module map replacing 4 duplicated Athena executors, 8+ duplicated CSV writers,
  and 4 duplicated HAR-entry loaders found in `github_copilot`; ports `PYTHON_DESIGN.md`'s DIP/OCP/SRP triggers into `Protocol` skeletons for `athena`, `report_render`, and `har`; adds a cross-project
  script registry generalizing `scratch-script-registry`'s duplicate-check pattern beyond `scratch/`. Not yet implemented — see its `tasks.md` for the first unchecked task (FCT-1). Sibling to
  `project-taxonomy` (categories vs. shared code) and `query-catalog` (SQL text vs. execution code).
- `docs/plan/reference-knowledge-harvest/` — story: the ongoing, docs-only vehicle for harvesting reusable knowledge out of `github_copilot`'s ~13 read-only investigation folders into
  `ih-trace-lab/knowledge/`, one folder per `RKH-N` task, never bundling folders together. First batch (`RKH-1`/`RKH-2`) covers `vod-asset-ingestion-mapping/` (VOD asset
  ADI↔OpsHub↔HAR↔Lightstep↔MongoDB field mapping, ID-navigation cheat sheet) plus the root `knowledge/{vod-asset-ingestion-pipeline,ctap-smvod-pipeline}.md` distillations that reference it;
  `applauseInvestigation`'s `lightstep-span-attributes-by-service.md` is left as a pointer, not harvested, for a future `RKH-N` task. Not yet implemented — see its `tasks.md` for the first unchecked
  task (RKH-1).
- `docs/plan/src-lib-migration/` — epic: real, tested implementations of `functional-code-taxonomy`'s six `src/lib/*` modules (`auth`, `athena`, `csv_io`, `report_render`, `har`, `curl_to_python`),
  ported/refactored from `github_copilot` (read-only reference), one story per module. `athena-lib-integration` is the exception — it wires in `/Users/abhadra/myWork/myOffice/athena-mcp-server` (an
  already-independent, tested repo with the shared `athena_runner` execution stack) as a git submodule and adapts to it, rather than re-porting a fifth copy of that logic.
  `auth`/`csv_io`/`curl_to_python` additionally define their own `Protocol`s here, deferred by `functional-code-taxonomy` FCT-2. Blocked on `functional-code-taxonomy` FCT-1/FCT-2/FCT-7 landing first.
  Not yet implemented — see `docs/plan/src-lib-migration/athena-lib-integration/tasks.md` for the first unchecked task (ALI-1).
- `docs/plan/pipeline-migration/` — epic: ports `aws-access-cli` (→ `src/pipelines/aws-access-cli/`, pipeline category, incl. PT-6 cron-cutover) and `ctap-smvod-session-report` (→
  `investigations/ctap-smvod/`, recurring-campaign category, incl. manual-Lightstep-step relocation) from `github_copilot` (read-only reference), replacing their duplicated executor/auth/SQL/output
  logic with `src/lib/*`, `query-catalog`, and `project-taxonomy` PT-7's ISO-prefix path convention respectively. Blocked on `project-taxonomy` PT-1/2/6/7, `src-lib-migration`, and `query-catalog`
  landing first. Not yet implemented — see `docs/plan/pipeline-migration/aws-access-cli-pipeline-migration/tasks.md` for the first unchecked task (AAM-1).
- `docs/plan/reference-code-gap-migration/` — story: a 2026-09-30 audit found 10 `github_copilot` projects (~166 Python files: `vod-playback-timing-probe`, `mtn-zm-session-device-investigation`,
  `mtn-network-traffic`, `vod-asset-ingestion-mapping`, root `investigations/`, `applauseInvestigation`, `shaka-6001-sa-error-analysis`, root `scripts/`, `astro-events-household-report`,
  `smarttv-mtntv`) with no migration plan in either `pipeline-migration` or `src-lib-migration` (which only cite a few of them as duplication *sources*, never port their business logic);
  `oasis-athena-mcp` was checked and confirmed not a gap (superseded by the `athena-mcp-server` submodule). Full file-by-file classification (lib-candidate vs. business-logic, ~35-45 files absorbable
  by the existing 7 `src/lib/*` modules, ~95-105 irreducible, several new-module candidates) is in this story's `spec.md`. Not yet implemented — see its `tasks.md` for the first unchecked task (GAP-1:
  decide scope shape — one epic vs. size-split — and resolve a `vod-asset-ingestion-mapping`/`vod-playback-timing-probe` category conflict with `project-taxonomy/structure.md`'s worked examples).

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
