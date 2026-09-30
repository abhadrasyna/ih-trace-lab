# astro-events-household-report migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: AEH-1.**

- [ ] **AEH-1** — Audit `astro-events-household-report/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **AEH-1** — both files (`inspect_sample_keys.py`, `pivot_distinct_values.py`) are classified with the FCT-1 test applied and stated, confirming or refining `spec.md` §9.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
