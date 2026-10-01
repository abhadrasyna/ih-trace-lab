# Flow-correlation-id logging — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none — story complete.**

- [x] **FCID-1** — Define the FCID convention (format, generation, `contextvars` propagation, log-line shape) | Owner: AI agent | Model: claude-sonnet-5 | Review: none | SHA: <pending commit>
- [x] **FCID-2** — Reference Mermaid diagrams + coordination notes in the 3 existing epics | Owner: AI agent | Model: claude-sonnet-5 | Review: none | SHA: <pending commit>

## Story done when

- **FCID-1** — `stories.md` states the FCID format, the single generation point per consumer type (pipeline/investigation/tool entry script), the `contextvars`-based propagation mechanism, and the
  exact structured-log-line shape (fields + example), with no detail left for an implementing session to invent.
- **FCID-2** — `stories.md` contains a rendering sequence diagram (one Athena query, one pipeline run) and a component diagram (FCID flowing through `src/lib/*` into all three epics' consumers);
  `src-lib-migration/README.md`, `pipeline-migration/README.md`, and `reference-code-gap-migration/README.md` each carry one dated coordination-note line pointing at this story.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update `CONTEXT.md`'s "What Exists" with one line for this story and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention — do not leave a done story half-archived.
