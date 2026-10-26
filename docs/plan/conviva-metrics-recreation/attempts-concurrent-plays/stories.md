# Attempts and Concurrent Plays — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

## CMR-ACP-1 — Scratch script computing attempts per time bucket from local session data

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Implement the definition from `definitions.md`; output a per-bucket CSV; record the method in the script header.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-acp-1`

---

## CMR-ACP-2 — Scratch script computing concurrent plays per time bucket

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Derive play start/end intervals from session events and count overlap per bucket; handle sessions with no end event explicitly.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-acp-2`

