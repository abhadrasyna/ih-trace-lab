# Metric Definitions and Data Inventory — prompt

> Capture Conviva's definitions for each target metric and map each to a data source.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Recreating a metric is only meaningful against its exact Conviva definition (what counts as an attempt, which errors count as VPF, when a play is concurrent). This story records those definitions and
inventories which local, Lightstep or Athena data can supply each input, so later stories do not guess. Part of the `conviva-metrics-recreation` epic; see `../README.md`.

## Scope guard

Docs and read-only inventory only. No scripts, no new data fetches beyond listing what exists. Out of bounds: `src/`, `scripts/`, `scratch/`.

## Session-start load hints

Conviva documentation supplied by the user; `docs/guides/tenant-resolution.md`; `docs/plan/session-trace-analysis/README.md`.

## Task overview

- **CMR-DEF-1** — Record Conviva definitions for attempts, concurrent plays, VPF, VSF and EBVS in a `definitions.md` in this folder, with doc references
- **CMR-DEF-2** — Inventory local data, Lightstep spans and Athena tables that can feed each metric, and list gaps in `inventory.md`

## Definition of done

CMR-DEF-1 is complete. CMR-DEF-2 is complete.

## Perspectives not covered

Conviva-side proprietary logic that is not publicly documented may not be reproducible.
