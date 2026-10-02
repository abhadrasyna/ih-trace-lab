# Pre-implementation design review — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` + `PYTHON_DESIGN.md`. After each task: set `SHA:` on the task
> line + tick the box, update the story status summary, add one line to your backlog/session-log file.

---

## PIR-1 — Deep review of src-lib-migration + pipeline-migration, apply autofixes

**Files to change / create:**
- `spec.md` — findings #1–10 (this task's output, already written).
- `src-lib-migration/athena-lib-integration/stories.md` — fix finding #1 (method-name mismatch).

**What to implement:**

1. Read all 6 `src-lib-migration` stories' `stories.md` and both `pipeline-migration` stories' `stories.md` in full; apply `PYTHON_DESIGN.md`'s SOLID-as-triggers checklist per story.
2. Record every finding in `spec.md` with a severity and disposition — **autofix** only when the fix is unambiguous and low-risk (a naming mismatch against an already-landed authoritative artifact; a
   missing cross-cutting-constraint line); everything else is **flagged**.
3. Apply finding #1's autofix: in `athena-lib-integration/stories.md`, rename ALI-2's class-diagram methods and task-text references from `run_query`/`download_results` to
   `start_query`/`fetch_results`, matching `src/lib/athena/protocols.py`'s `AthenaClient` exactly (`poll_status` was already consistent).

**Tests:** N/A — design-review task, no code.

**Commit:** `docs(design-review): review src-lib-migration + pipeline-migration, fix ALI method-name mismatch`

---

## PIR-2 — Process-parity check of reference-code-gap-migration, apply the one autofix

**Files to change / create:**
- `spec.md` — finding #11 (this task's output, already written).
- `reference-code-gap-migration/README.md` — fix finding #11 (design-time-diagram parity constraint).

**What to implement:**

1. Confirm (spot-check at least 2 of the 10 sub-stories' `tasks.md`) that no concrete `Protocol`/class-diagram design exists yet beyond each sub-story's audit-only first task — this bounds the review
   to a process check, not a line-level critique.
2. Apply finding #11's autofix: add one line to `reference-code-gap-migration/README.md`'s "Cross-cutting constraints" section requiring every sub-story's 2nd+ task to author class/sequence Mermaid
   diagrams in its own `stories.md` before any code, mirroring `src-lib-migration`'s own stated discipline.

**Tests:** N/A — design-review task, no code.

**Commit:** `docs(design-review): add design-time-diagram parity constraint to reference-code-gap-migration`

---

## PIR-3 — Consolidate flagged findings, update CONTEXT.md

**Files to change / create:**
- `spec.md` — "Flagged for human decision" section (this task's output, already written).
- `CONTEXT.md` — one new "What Exists" line for this story.

**What to implement:**

1. Re-read `spec.md`'s full findings table; confirm every **flagged** disposition has a corresponding, self-contained entry in "Flagged for human decision" (decision needed + file(s) it would touch) —
   a human must be able to act without re-reading this story's session transcript.
2. Add the `CONTEXT.md` line summarizing this story's outcome: 2 autofixes applied, 6 findings flagged for human decision, pointer to `spec.md`.

**Tests:** N/A — docs only.

**Commit:** `docs(design-review): consolidate flagged findings, update CONTEXT.md`
