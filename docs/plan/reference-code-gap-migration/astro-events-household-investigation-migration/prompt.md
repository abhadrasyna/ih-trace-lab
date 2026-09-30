# astro-events-household-report migration — prompt

> Port `astro-events-household-report` (Astro event/household CSV key inspection + distinct-value pivoting) into `investigations/astro-events-household/` — Tier 1, near-zero-effort, both files
> absorbable by `csv_io`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/astro-events-household-report` (2 files) has no migration plan anywhere. Epic `spec.md` §9 audited both files: `inspect_sample_keys.py` and `pivot_distinct_values.py`
are both `csv_io` lib candidates; no project-specific business logic and no new module required.

## Scope guard

**In bounds:** `investigations/astro-events-household/` — auditing/confirming `spec.md` §9's classification, then (later) skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/astro-events-household-report` (read-only, never edited); `src/lib/csv_io` internals; any other sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §9 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (Tier 1).
- `docs/plan/project-taxonomy/structure.md` — `investigations/<slug>/` skeleton; this project needs a new campaign slug (`astro-events-household`, not yet worked-example'd there).
- `docs/plan/src-lib-migration/README.md` — `csv_io` module status.

## Task overview

- **AEH-1** — Audit `astro-events-household-report/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §9.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`investigations/astro-events-household/` exists, fully tested, both scripts importing `src/lib/csv_io` with no local re-implementation of CSV load/pivot logic. No file under
`/Users/abhadra/github_copilot` was touched.
