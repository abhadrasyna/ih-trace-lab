# Curl to python lib migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CPM-1, CPM-2, CPM-3, CPM-4, CPM-5.**

- [ ] **CPM-1** — Confirm/derive replaced-originals citation from FCT-1 audit | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **CPM-2** — `src/lib/curl_to_python/protocols.py`: new `CurlConverterProtocol` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **CPM-3** — `src/lib/curl_to_python/converter.py`: concrete implementer | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **CPM-4** — Tests + `Protocol` conformance pair | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **CPM-5** — Doc/`CONTEXT.md` pointers | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **CPM-1** — A recorded finding states either the specific `github_copilot` files this module replaces, or explicitly that none were cited in FCT-1's audit and this module is built ahead of a
  proven-duplication trigger (per this epic's explicit authorization, not a silent scope assumption).
- **CPM-2** — `src/lib/curl_to_python/protocols.py` defines `CurlConverterProtocol` as a `Protocol`-only interface, `@runtime_checkable`.
- **CPM-3** — `src/lib/curl_to_python/converter.py` implements it with a pure, side-effect-free conversion (parses/produces text or AST only, never executes the converted request).
- **CPM-4** — `pytest` passes; `Protocol` conformance confirmed via `isinstance`.
- **CPM-5** — `CONTEXT.md` gains one new "What Exists" line; epic `README.md` status table updated to ✅ Done with closing SHA.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` "Stories" table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention.
