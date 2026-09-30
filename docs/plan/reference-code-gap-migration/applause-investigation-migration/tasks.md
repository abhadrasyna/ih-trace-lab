# applauseInvestigation migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: APL-1.**

- [ ] **APL-1** — Audit `applauseInvestigation/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **APL-1** — every file under `applauseInvestigation/scripts/` is classified as either a `src/lib/*` consumer point or project-specific business logic, with the FCT-1 test applied and stated per
  file, confirming or refining `spec.md` §6's existing table rather than assuming it.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
