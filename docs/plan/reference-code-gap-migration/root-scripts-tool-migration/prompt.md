# root scripts migration — prompt

> Port root `github_copilot/scripts/` (repository maintenance and knowledge/report-generation utilities) into `src/tools/repo-maintenance/` — Tier 1, cheap, no new module.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/scripts/` (4 files: `disk_usage.py`, `generate_scripts_registry.py`, `reflow_markdown.py`, `update_athena_table_ddl_knowledge.py`) has no migration plan anywhere. Epic
`spec.md` §8 audited it: only `update_athena_table_ddl_knowledge.py` is a `csv_io`/`report_render` lib candidate; the other 3 are repository-specific maintenance tools.

## Scope guard

**In bounds:** `src/tools/repo-maintenance/` — auditing/confirming `spec.md` §8's classification, then (later) skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/scripts` (read-only, never edited); `src/lib/*` internals; `functional-code-taxonomy` FCT-6's own script registry (this story only
checks for overlap, never edits FCT-6's files).

**Coordination check required before porting `generate_scripts_registry.py`:** `ih-trace-lab` already has its own `scripts/dev/generate_scripts_registry.py` (existing convergence-rule tooling) and
`functional-code-taxonomy` FCT-6 extends that registry across `investigations/*/scripts`, `experiments/*/scripts`, `src/pipelines`, `src/tools`. The first task must check whether the `github_copilot`
version is already fully superseded by that existing/planned tooling before deciding to port a second copy — if superseded, note that in the audit and drop it from the port list rather than
duplicating it a second time.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §8 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (Tier 1; FCT-6 coordination note).
- `docs/plan/functional-code-taxonomy/` — FCT-6's own spec, to check the `generate_scripts_registry.py` overlap.
- `docs/plan/src-lib-migration/README.md` — `csv_io`/`report_render` module status.

## Task overview

- **RSC-1** — Audit `github_copilot/scripts/` and produce a per-file lib-vs-script classification table, including the FCT-6 overlap check for `generate_scripts_registry.py`.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`src/tools/repo-maintenance/` exists, fully tested, `update_athena_table_ddl_knowledge.py` importing `src/lib/{csv_io,report_render}`; `disk_usage.py`/`reflow_markdown.py` stay local;
`generate_scripts_registry.py` either ported (if not superseded) or explicitly dropped with a documented FCT-6-supersession reason. No file under `/Users/abhadra/github_copilot` was touched.
