# vod-playback-timing-probe migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: VTP-1.**

- [ ] **VTP-1** — Audit `vod-playback-timing-probe/scripts/` and produce a per-file lib-vs-script classification table (audit-only, blocked on `src/lib/mpd/` for any actual port) | Owner: AI agent
  | Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **VTP-1** — every implementation file under `vod-playback-timing-probe/scripts/` is classified with the FCT-1 test applied and stated, confirming or refining `spec.md` §1; the `mpd`-dependent subset
  is explicitly flagged as blocked pending `src/lib/mpd/`.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
