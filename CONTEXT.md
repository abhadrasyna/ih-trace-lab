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

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
