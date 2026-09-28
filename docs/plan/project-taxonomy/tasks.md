# Project taxonomy — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: PT-1, PT-2, PT-3, PT-4, PT-5.**

- [ ] **PT-1** — `docs/guides/project-taxonomy.md`: five categories + `github_copilot` examples | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-2** — same doc: per-category folder skeleton + submodule-vs-plain-folder rule | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-3** — same doc: new-investigation checklist with mandatory prior-art search | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>
- [ ] **PT-4** — `scripts/dev/check_project_taxonomy.py` + tests | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human confirms tests green | SHA: <—>
- [ ] **PT-5** — `AGENTS.md` + `CONTEXT.md` pointer lines | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **PT-1** — `docs/guides/project-taxonomy.md` exists with a named, one-paragraph definition for each of: pipeline, continuous investigation, one-off investigation, tool, experiment — each citing the
  specific `github_copilot` folder it is modeled on.
- **PT-2** — The same doc has a table (one row per category) listing required files/folders for that category, and a short decision rule stating exactly when new work becomes a git submodule vs. a
  plain folder (the "own instructions file / independent cadence" test from `prompt.md`'s findings).
- **PT-3** — The same doc has a checklist a session follows before creating any new top-level folder: (1) pick a category via the PT-1 decision tree, (2) delegate a sub-agent to search `docs/guides/`,
  `knowledge/` (once it exists), and `/Users/abhadra/github_copilot` (read-only) for prior art on the same question, (3) only create the folder if no reusable prior art is found or reuse/extend what
  is found instead.
- **PT-4** — `python scripts/dev/check_project_taxonomy.py` runs against the repo root, lists top-level dirs, and flags any that match none of the PT-2 category markers; its tests cover a fixture tree
  with one matching and one unmatched directory.
- **PT-5** — `AGENTS.md` gained one pointer line to `docs/guides/project-taxonomy.md`; `CONTEXT.md`'s "What Exists" list gained one line describing this story's status.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per this project's own convention — do not leave a done story half-archived.
