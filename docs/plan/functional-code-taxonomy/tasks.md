# Functional code taxonomy — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: FCT-1, FCT-2, FCT-3, FCT-4, FCT-5.**

- [ ] **FCT-1** — `docs/guides/functional-code-taxonomy.md`: six-module map + replaced-originals evidence | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA:
  <—>
- [ ] **FCT-2** — `src/lib/athena/protocols.py` + `src/lib/report_render/protocols.py`: `Protocol` skeletons + tests | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms
  tests green | SHA: <—>
- [ ] **FCT-3** — same doc: migration/ownership table + query-catalog boundary | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **FCT-4** — `AGENTS.md` pointer line | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **FCT-5** — `CONTEXT.md` pointer line | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **FCT-1** — `docs/guides/functional-code-taxonomy.md` names `src/lib/{auth,athena,csv_io,report_render,har,curl_to_python}/`, each with a one-paragraph responsibility and at least one specific
  `github_copilot` file it is meant to replace (e.g. `athena` cites all three duplicated executors by path).
- **FCT-2** — Both `protocols.py` files define `Protocol` classes only (`abc`/`typing.Protocol`, `@runtime_checkable` where instance checks are meaningful) with method signatures but no bodies beyond
  `...`; `pytest` confirms a minimal hand-written conforming class satisfies each `Protocol` via `isinstance`, and a non-conforming stub does not.
- **FCT-3** — The guide doc has a table mapping each `docs/plan/project-taxonomy/` category to which `src/lib/*` modules it consumes, plus one explicit sentence: "`query-catalog` owns SQL text; this
  story owns the code that executes it."
- **FCT-4** — `AGENTS.md` gained one pointer line stating `docs/guides/functional-code-taxonomy.md` is where `PYTHON_DESIGN.md`'s triggers are applied concretely.
- **FCT-5** — `CONTEXT.md`'s "What Exists" list gained one line for this story, matching the existing `tenant-registry`/`query-catalog` bullet style.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per this project's own convention — do not leave a done story half-archived.
