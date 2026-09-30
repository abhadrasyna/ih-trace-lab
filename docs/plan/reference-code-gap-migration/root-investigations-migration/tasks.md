# root investigations migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: RIN-1.**

- [ ] **RIN-1** — Audit root `investigations/scripts/` and produce a per-file lib-vs-script classification table, incl. Jira-script reconciliation | Owner: AI agent | Model: n/a | Review: human
  read-through | SHA: <—>

## Story done when

- **RIN-1** — every file under root `investigations/scripts/` is classified with the FCT-1 test applied and stated, confirming or refining `spec.md` §5; `extract_jira.py`/`extract_jira2.py`'s
  duplication is resolved to a single target script (state which one, and why) rather than carrying both forward.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
