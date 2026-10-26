# Attempts and Concurrent Plays — prompt

> Recreate Conviva's attempts and concurrent-plays statistics from session data.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Attempts is the denominator for most Conviva ratios and concurrent plays is the capacity view, so both must be right before failure metrics are meaningful. Part of the `conviva-metrics-recreation`
epic; see `../README.md`.

## Scope guard

Scratch scripts only, under `scratch/`; no changes to `src/`. Read-only data access.

## Session-start load hints

`../metric-definitions-data-inventory/definitions.md` and `inventory.md`; `scratch/SCRATCH.md`; `docs/guides/query-catalog.md`.

## Task overview

- **CMR-ACP-1** — Scratch script computing attempts per time bucket from local session data
- **CMR-ACP-2** — Scratch script computing concurrent plays per time bucket

## Definition of done

CMR-ACP-1 is complete. CMR-ACP-2 is complete.

## Perspectives not covered

Cross-device or cross-tenant deduplication.
