# Metric Definitions and Data Inventory — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. After each task: set `SHA:` on the task line + tick the box, update the epic `README.md` status, add one
> line to the backlog/session-log file.

## CMR-DEF-1 — Record Conviva definitions for attempts, concurrent plays, VPF, VSF and EBVS in a `definitions.md` in this folder, with doc references

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. Collect Conviva docs from the user; quote or paraphrase each definition with a source link; note ambiguities as open questions.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-def-1`

---

## CMR-DEF-2 — Inventory local data, Lightstep spans and Athena tables that can feed each metric, and list gaps in `inventory.md`

**Files to change / create:**
- See the task title; docs go in this story folder, scratch scripts under `scratch/` with a registry stub per `scratch/SCRATCH.md`.

**What to implement:**

1. For each metric input map to a field in local session data, a Lightstep attribute or an Athena column; run the tenant-resolution step before any remote lookup; list what must be fetched.
2. Confirm scope and plan with the user before creating or editing anything (project Steps 2-3).

**Tests (no network, no real external services):**
- Docs tasks: none beyond the docs-plan pre-commit hooks.
- Scratch scripts: exempt from the test gate until graduation; verify by running on local data and recording the output. Fixture-based happy-path and edge-case tests are written at graduation.

**Commit:** `docs(conviva-metrics): cmr-def-2`

