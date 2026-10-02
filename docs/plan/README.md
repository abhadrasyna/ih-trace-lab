# `docs/plan/` — story and epic tracking

One folder per unit of work. See `_TEMPLATE/README.md` for how to start a new one.

## Conventions

### Story-folder file set

A story folder is a leaf: it has its own `prompt.md` (why the story exists, what task to do next) and a working task list. Required:

| File | Required? | Holds |
|---|---|---|
| `prompt.md` | required | Why the story exists, session-start instructions, task overview. |
| `tasks.md` | required | The working checkbox list — one `- [ ]`/`- [x]` per task id, top to bottom. |
| `stories.md` | required | Per-task spec: files to change, what to implement, tests, commit message. |
| `schema.md` | conditional | DDL, when the story changes persistent-storage schema. |
| `plan.md` / `spec.md` | optional | File-by-file plan for a large story — no task checkboxes. |

### Epic-folder file set

An epic is a container: `prompt.md` (router — lists its stories in fixed order) + `README.md` (shared brief) at the root, plus one story sub-folder per story. The epic root carries **no `tasks.md`**
of its own — every checkbox lives in a sub-story's `tasks.md`.

**Phase0 workflow:** stories are created standalone at the top level of `docs/plan/` (`docs/plan/<slug>/` with `prompt.md` + `tasks.md` + `stories.md`) — no epic wrapper required. Once a handful of
related stories exist, they may be moved together under a new epic folder (`prompt.md` + `README.md` router, stories nested underneath). Until that grouping decision is made, go with plain story
folders only.

### Extra files

No tracked non-`.md` file belongs in a plan folder. An extra `.md` beyond the sets above must not carry `- [ ]` task checkboxes — those belong in `tasks.md` only, so nothing mirrors task state and
nothing can drift.

### Task-line format

Each task id (`**ID**`) carries exactly one checkbox, in `tasks.md`'s working list. A `## Story done when` / `## Epic done when` summary block is prose criteria only — no checkboxes there.

### Archiving a completed story

Once a standalone story's `tasks.md` shows `**Open: none — story complete.**` (and, for a story nested under an epic, once every one of the epic's sub-stories shows the same marker — the epic folder
stays under `docs/plan/` until all of its stories are done), archive it with the script:

```
python scripts/dev/archive_completed_story.py <slug>
```

It `git mv`s the folder to `docs/archive/<slug>`, rewrites every `docs/plan/<slug>` cross-reference (in other stories' `prompt.md`/`stories.md`/`tasks.md`, `CONTEXT.md`, `README.md`, and any
`docs/guides/*`) to `docs/archive/<slug>`, reflows any line pushed over the 200-char cap by the longer path, and stages every touched file with `git add` — it does not commit, and refuses to run
(raises `StoryNotComplete`) if the slug or any of its sub-stories is still open. Review `git status`, then commit the move and every reference update together in one commit.

A non-blocking `story-archive-check` pre-commit hook (`scripts/dev/hooks/check_unarchived_stories.py`) warns — without blocking the commit — whenever a `docs/plan/` story or epic looks complete but
hasn't been archived yet, as a safety net for the case where this step is forgotten.

2026-10-02: first applied manually to `tenant-registry`, `query-catalog`, `project-taxonomy`, `functional-code-taxonomy`, `scratch-script-registry`, `reference-knowledge-harvest`,
`reference-folder-diagrams`, `flow-correlation-id-logging`, and `pre-implementation-design-review`, before the script above existed.

### Autopilot mode (running a multi-story epic in one sitting)

See root `AUTOMATION.md` for the full how-to. The short version, specific to `docs/plan/` structure: an epic's stories are independently scoped by design (own `prompt.md`/`tasks.md`/`stories.md`, own
first-unchecked-task), so each story is a natural sub-agent delegation unit — a fresh agent per story, reading only that story's own files plus the epic `README.md`, never the whole epic's accumulated
transcript. The `src-lib-migration` epic (2026-10-02) was instead driven as 24 task segments inside one single-agent session with no re-check between segments, which produced the
`re-read-context-on-resumed-task-segments`/`state-plan-before-editing`/`wait-for-explicit-go-ahead-before-editing` rows now ranked highly in root `suggestions.md`.
`scripts/dev/hooks/autopilot_checkpoint.py` (`.github/hooks/autopilot-checkpoint.json`) now forces a plan/go-ahead checkpoint every 5 agent turns as a backstop, but delegating story-by-story to
sub-agents avoids needing that backstop to fire at all — each sub-agent's own first turn already satisfies Step 1-3 fresh, and its context never accumulates the prior stories' token cost.
