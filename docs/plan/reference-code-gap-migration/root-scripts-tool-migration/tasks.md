# root scripts migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: RSC-1.**

- [ ] **RSC-1** — Audit `github_copilot/scripts/` and produce a per-file lib-vs-script classification table, incl. FCT-6 overlap check | Owner: AI agent | Model: n/a | Review: human read-through |
  SHA: <—>

## Story done when

- **RSC-1** — every file (`disk_usage.py`, `generate_scripts_registry.py`, `reflow_markdown.py`, `update_athena_table_ddl_knowledge.py`) is classified with the FCT-1 test applied and stated,
  confirming or refining `spec.md` §8, and `generate_scripts_registry.py`'s overlap with `functional-code-taxonomy` FCT-6 is explicitly resolved (ported vs. dropped as superseded).

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
