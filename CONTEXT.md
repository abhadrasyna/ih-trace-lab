# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `docs/plan/tenant-registry/` — story: canonical MTN tenant-identifier config (Go ID, Matisse Project/Client Tenant ID, Athena Tenant ID, Lightstep project/region, shared-project disambiguation) + a
  resolver this assistant must consult before any Lightstep/Matisse/Athena MCP call. Not yet implemented — see its `tasks.md` for the first unchecked task (TR-1).
- `docs/plan/query-catalog/` — story: `queries/athena/` + `queries/lightstep/` deduplicated, parameterized-template query catalog (harvested from `github_copilot`'s 3 `QUERY_CATALOG.md` files +
  `lightstep-query-templates.md`), plus a ported (not yet run) Athena DDL-cache under `knowledge/`. Not yet implemented — see its `tasks.md` for the first unchecked task (QC-1). Its DDL-cache task
  (QC-4) depends on `tenant-registry` landing first for any live Athena discovery.
- `docs/plan/project-taxonomy/` — story: classifies work into 5 categories (pipeline, continuous investigation, one-off investigation, tool, experiment), per-category folder skeleton, the
  submodule-vs-plain-folder rule, a new-work checklist with a mandatory prior-art search step, and a pipeline cron-cutover procedure (for `aws-access-cli`-style live crontab migrations) — informed by
  a `github_copilot` audit (read-only reference). Not yet implemented — see its `tasks.md` for the first unchecked task (PT-1).
- `docs/plan/functional-code-taxonomy/` — story: target `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/` module map replacing 3 duplicated Athena executors and 8+ duplicated CSV
  writers found in `github_copilot`; ports `PYTHON_DESIGN.md`'s DIP/OCP triggers into `Protocol` skeletons for `athena` and `report_render`. Not yet implemented — see its `tasks.md` for the first
  unchecked task (FCT-1). Sibling to `project-taxonomy` (categories vs. shared code) and `query-catalog` (SQL text vs. execution code).

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- `/Users/abhadra/github_copilot` is read-only reference (see `README.md`'s mission statement) — never create, edit, or delete anything there from this project; treat it as prior art to learn the
  "profile of work" from, not a shared codebase.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
