# VPF and VSF — prompt

> Recreate video playback failures (VPF) and video start failures (VSF) with an explicit error classification.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

VPF and VSF depend on which errors Conviva counts as fatal and whether they occur before or after video start. That mapping is the hard part, so it is documented as a table before it is coded. Part of
the `conviva-metrics-recreation` epic; see `../README.md`.

## Scope guard

Scratch scripts and a classification doc only; no changes to `src/`. Reuse `docs/plan/session-trace-analysis/session-error-model/` rather than re-deriving error taxonomy.

## Session-start load hints

`../metric-definitions-data-inventory/definitions.md`; the session-error-model story; `scratch/SCRATCH.md`.

## Task overview

- **CMR-VF-1** — Write `error-classification.md` mapping our error events to VPF, VSF or neither
- **CMR-VF-2** — Scratch script computing VPF and VSF counts and rates per time bucket

## Definition of done

CMR-VF-1 is complete. CMR-VF-2 is complete.

## Perspectives not covered

Conviva's handling of fatal versus non-fatal errors that are invisible in our traces.
