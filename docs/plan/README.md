# `docs/plan/` — story and epic tracking

One folder per unit of work. See `_TEMPLATE/README.md` for how to start a new one.

## Conventions

### Story-folder file set

A story folder is a leaf: it has its own `prompt.md` (why the story exists, what task to
do next) and a working task list. Required:

| File | Required? | Holds |
|---|---|---|
| `prompt.md` | required | Why the story exists, session-start instructions, task overview. |
| `tasks.md` | required | The working checkbox list — one `- [ ]`/`- [x]` per task id, top to bottom. |
| `stories.md` | required | Per-task spec: files to change, what to implement, tests, commit message. |
| `schema.md` | conditional | DDL, when the story changes persistent-storage schema. |
| `plan.md` / `spec.md` | optional | File-by-file plan for a large story — no task checkboxes. |

### Epic-folder file set

An epic is a container: `prompt.md` (router — lists its stories in fixed order) +
`README.md` (shared brief) at the root, plus one story sub-folder per story. The epic
root carries **no `tasks.md`** of its own — every checkbox lives in a sub-story's
`tasks.md`.

**Phase0 workflow:** stories are created standalone at the top level of `docs/plan/`
(`docs/plan/<slug>/` with `prompt.md` + `tasks.md` + `stories.md`) — no epic wrapper
required. Once a handful of related stories exist, they may be moved together under a
new epic folder (`prompt.md` + `README.md` router, stories nested underneath). Until
that grouping decision is made, go with plain story folders only.

### Extra files

No tracked non-`.md` file belongs in a plan folder. An extra `.md` beyond the sets above
must not carry `- [ ]` task checkboxes — those belong in `tasks.md` only, so nothing
mirrors task state and nothing can drift.

### Task-line format

Each task id (`**ID**`) carries exactly one checkbox, in `tasks.md`'s working list. A
`## Story done when` / `## Epic done when` summary block is prose criteria only — no
checkboxes there.
