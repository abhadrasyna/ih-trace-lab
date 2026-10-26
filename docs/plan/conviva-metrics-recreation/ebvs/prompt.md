# EBVS (Exits Before Video Start) — prompt

> Recreate EBVS and keep it distinct from VSF.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

EBVS counts attempts abandoned before video starts without a reported error, so it is the complement of VSF in the start funnel. Mixing them inflates one and hides the other. Part of the
`conviva-metrics-recreation` epic; see `../README.md`.

## Scope guard

Scratch scripts only; no changes to `src/`. Depends on the attempts logic from `attempts-concurrent-plays`.

## Session-start load hints

`../metric-definitions-data-inventory/definitions.md`; `../attempts-concurrent-plays/`; `docs/plan/session-trace-analysis/session-presence-funnel/`.

## Task overview

- **CMR-EBVS-1** — Scratch script computing EBVS per time bucket
- **CMR-EBVS-2** — Document the EBVS versus VSF boundary with worked examples from real sessions

## Definition of done

CMR-EBVS-1 is complete. CMR-EBVS-2 is complete.

## Perspectives not covered

Exit-time thresholds (for example, how long a session may idle before counting as an exit).
