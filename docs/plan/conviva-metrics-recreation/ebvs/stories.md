# EBVS (Exits Before Video Start) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

## CMR-EBVS-1 — Scratch script computing EBVS per time bucket

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Count attempts with no video-start event and an exit signal and no error classified as VSF; document the exit signal used.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-ebvs-1`

---

## CMR-EBVS-2 — Document the EBVS versus VSF boundary with worked examples from real sessions

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Pick at least three sessions per class from local data and show the events that place each on its side.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-ebvs-2`

