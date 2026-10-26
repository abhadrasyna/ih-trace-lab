# VPF and VSF — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

## CMR-VF-1 — Write `error-classification.md` mapping our error events to VPF, VSF or neither

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Cite the Conviva rule for each row; flag rows where our events cannot distinguish pre- and post-start.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-vf-1`

---

## CMR-VF-2 — Scratch script computing VPF and VSF counts and rates per time bucket

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Apply the classification; rate denominators come from the attempts script; output per-bucket CSV.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-vf-2`

