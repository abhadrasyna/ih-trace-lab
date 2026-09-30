# Report render lib migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: RRM-1, RRM-2, RRM-3, RRM-4.**

- [ ] **RRM-1** — Re-confirm 8+ file audit list, group by report shape | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **RRM-2** — `src/lib/report_render/writers.py`: Strategy implementer(s) satisfying FCT-2's `Protocol` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests
  green | SHA: <—>
- [ ] **RRM-3** — Tests + `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **RRM-4** — Doc/`CONTEXT.md` pointers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **RRM-1** — A confirmed shape-grouped list exists (in `stories.md`'s RRM-2 section or a short note), citing each of the original 8+ files or explaining any drift since the FCT-1 audit.
- **RRM-2** — `src/lib/report_render/writers.py` provides one Strategy implementer per distinct report shape, each satisfying FCT-2's `Protocol`.
- **RRM-3** — `pytest` passes; a `Protocol`-conformance test confirms `isinstance` behavior for a conforming and a non-conforming stub.
- **RRM-4** — `CONTEXT.md` gains one new "What Exists" line; epic `README.md` status table updated to ✅ Done with closing SHA.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
