# Har lib migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: HLM-1, HLM-2, HLM-3, HLM-4.**

- [ ] **HLM-1** — Re-confirm 4-copy audit list | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **HLM-2** — `src/lib/har/loader.py`: concrete loader satisfying FCT-2's `Protocol` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **HLM-3** — Tests + `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **HLM-4** — Doc/`CONTEXT.md` pointers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **HLM-1** — A confirmed list of the four originals (with file citations) is recorded in `stories.md`, noting any drift since the FCT-1 audit.
- **HLM-2** — `src/lib/har/loader.py` provides a single loader function/class covering all four originals' behavior, satisfying FCT-2's `Protocol`.
- **HLM-3** — `pytest` passes using fixture HAR files; a `Protocol`-conformance test confirms `isinstance` behavior for a conforming and a non-conforming stub.
- **HLM-4** — `CONTEXT.md` gains one new "What Exists" line; epic `README.md` status table updated to ✅ Done with closing SHA.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
