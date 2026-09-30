# vod-asset-ingestion-mapping migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: VAI-1.**

- [ ] **VAI-1** — Audit `vod-asset-ingestion-mapping/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **VAI-1** — every file under `vod-asset-ingestion-mapping/scripts/` (incl. `lib/`) is classified with the FCT-1 test applied and stated, confirming or refining `spec.md` §4.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
