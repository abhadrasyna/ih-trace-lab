# Scratch Validation Against Conviva — prompt

> Compare recomputed metrics with Conviva's reported numbers and log every discrepancy.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A recreated metric is only trusted once it matches Conviva on a real window. This story does that comparison and decides what graduates from `scratch/` to `src/`. Part of the
`conviva-metrics-recreation` epic; see `../README.md`.

## Scope guard

Comparison script and a findings doc; no changes to `src/` until a separate graduation go-ahead.

## Session-start load hints

Outputs of all earlier stories; a Conviva export for a chosen window, supplied by the user.

## Task overview

- **CMR-VAL-1** — Scratch script comparing recomputed per-bucket metrics with a Conviva export
- **CMR-VAL-2** — Write `findings.md` explaining discrepancies and recommending which scripts graduate

## Definition of done

CMR-VAL-1 is complete. CMR-VAL-2 is complete.

## Perspectives not covered

Ongoing scheduled comparison; this is a one-window validation.
