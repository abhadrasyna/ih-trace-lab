# applauseInvestigation migration — prompt

> Port `applauseInvestigation` (Applause issue exports, Lightstep CSVs, Athena playback/debug-event data, HAR captures, reproduction-run organizing) into `investigations/applause/` — Tier 1,
> near-zero-effort once `src-lib-migration` lands (see epic `README.md`).

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/applauseInvestigation` (9 files) is a recurring campaign — Applause 3rd-party test issue triage — with no migration plan in `pipeline-migration` or `src-lib-migration`
(cited there only as a duplication *source*). Epic `spec.md` §6 audited it file-by-file: 8 of 9 files are lib candidates (`athena`, `csv_io`, `har`, `report_render`, `paths`), 1
(`analyze_athena_playback.py`) keeps applause-specific correlation semantics even while consuming `athena`/`csv_io`. No new `src/lib/*` module is required.

## Scope guard

**In bounds:** `investigations/applause/` (already named in `project-taxonomy/structure.md`'s worked example) — auditing/confirming `spec.md` §6's classification, then (in a later task) the actual
skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/applauseInvestigation` (read-only, never edited); `src/lib/*` internals (consumed as-is); any other sub-story in this epic.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §6 — this project's full per-file audit table; read before the first task.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log and story table (this story is Tier 1).
- `docs/plan/project-taxonomy/structure.md` — the `investigations/<campaign-slug>/` skeleton (Rule A/B) this story's target folder must match.
- `docs/plan/src-lib-migration/README.md` — confirms which `src/lib/*` modules exist before importing them.

## Task overview

- **APL-1** — Audit `applauseInvestigation/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §6.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) are deliberately not yet written — they depend on APL-1's confirmed classification and on `src-lib-migration` having landed.

## Definition of done

`investigations/applause/` exists, fully tested, importing `src/lib/{athena,csv_io,har,report_render,paths}` for every domain-mechanism concern; applause-specific correlation logic
(`analyze_athena_playback.py`'s issue/session matching) stays local. No file under `/Users/abhadra/github_copilot` was touched.
