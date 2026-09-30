# Auth lib migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: AUM-1, AUM-2, AUM-3, AUM-4.**

- [ ] **AUM-1** — `src/lib/auth/protocols.py`: new `AuthProtocol` generalized from `athena_runner.sso_auth` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests
  green | SHA: <—>
- [ ] **AUM-2** — `src/lib/auth/sso.py`: concrete implementer delegating to `athena_runner.sso_auth` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green |
  SHA: <—>
- [ ] **AUM-3** — Tests + `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **AUM-4** — Doc/`CONTEXT.md` pointers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **AUM-1** — `src/lib/auth/protocols.py` defines `AuthProtocol` as a `Protocol`-only interface, `@runtime_checkable`, matching FCT-2's authoring style; a conformance test pair exists.
- **AUM-2** — `src/lib/auth/sso.py` implements `AuthProtocol` by delegating to `athena_runner.sso_auth`'s public surface — no duplicated SSO refresh logic.
- **AUM-3** — `pytest` passes with no live AWS calls; `Protocol` conformance confirmed via `isinstance`.
- **AUM-4** — `CONTEXT.md` gains one new "What Exists" line; epic `README.md` status table updated to ✅ Done with closing SHA.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
