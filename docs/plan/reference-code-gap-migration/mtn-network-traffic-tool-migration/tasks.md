# mtn-network-traffic migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MNT-1.**

- [ ] **MNT-1** — Audit `mtn-network-traffic/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **MNT-1** — every file under `mtn-network-traffic/scripts/` (incl. `curl_timer/` package) is classified with the FCT-1 test applied and stated, confirming or refining `spec.md` §3, and the
  network-diagnostics accept-local decision is re-confirmed (no new third consumer found).

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
