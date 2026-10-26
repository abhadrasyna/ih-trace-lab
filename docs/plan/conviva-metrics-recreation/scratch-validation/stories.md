# Scratch Validation Against Conviva — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

## CMR-VAL-1 — Scratch script comparing recomputed per-bucket metrics with a Conviva export

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Inputs by argparse: recomputed CSVs and the Conviva export; output per-metric delta and percent difference.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-val-1`

---

## CMR-VAL-2 — Write `findings.md` explaining discrepancies and recommending which scripts graduate

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Classify each gap as definition mismatch, data gap or Conviva-side logic; list graduation candidates for the user to approve.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-val-2`

