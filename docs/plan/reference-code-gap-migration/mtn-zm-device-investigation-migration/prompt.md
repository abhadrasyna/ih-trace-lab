# mtn-zm-session-device-investigation migration — prompt

> Port `mtn-zm-session-device-investigation` (tenant-configured Athena pipeline correlating session records, debug events, error codes, device/session outcomes) into `investigations/mtn-zm-device/` —
> Tier 2.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/mtn-zm-session-device-investigation` (32 files: 19 implementation + 13 tests) has no migration plan anywhere. Epic `spec.md` §2 audited it: approximately 10
implementation files fit existing `athena`/`csv_io`/`report_render`/`paths`; approximately 9 are case-specific (tenant/query registry, session-outcome classification, error-code extraction, pipeline
orchestration).

**Correction to `stories.md`'s own hypothesis (epic GAP-1, 2026-09-30):** the epic prompt's step 2 hypothesized this project "needs net-new modules first," alongside `vod-playback-timing-probe`.
`spec.md`'s evidence does not support that for this project — its rollup names tenant/query-registry abstractions and session-outcome classification as business logic *beyond* generic Athena
execution, not a missing shared mechanism. This story is Tier 2 (no new module blocking it), not Tier 3.

## Scope guard

**In bounds:** `investigations/mtn-zm-device/` (already named in `project-taxonomy/structure.md`'s worked example) — auditing/confirming `spec.md` §2's classification, then (later) skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/mtn-zm-session-device-investigation` (read-only, never edited); `src/lib/{athena,csv_io,report_render,paths}` internals; any other
sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §2 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` — epic decision log (Tier 2 correction, above).
- `docs/plan/project-taxonomy/structure.md` — the existing `investigations/mtn-zm-device/` worked example.
- `docs/plan/src-lib-migration/README.md` — `athena`/`csv_io`/`report_render`/`paths` module status.

## Task overview

- **MZD-1** — Audit `mtn-zm-session-device-investigation/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §2.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`investigations/mtn-zm-device/` exists, fully tested, importing `src/lib/{athena,csv_io,report_render,paths}` for domain-mechanism concerns; tenant/query registry, session-outcome classification,
error-code extraction, and pipeline orchestration stay local business logic. No file under `/Users/abhadra/github_copilot` was touched.
