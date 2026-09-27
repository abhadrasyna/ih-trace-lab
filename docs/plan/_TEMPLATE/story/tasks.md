<!-- Copy the whole `story/` folder to docs/plan/<slug>/ (single story) or
docs/plan/<epic-slug>/<story-slug>/ (epic sub-story). Delete these HTML comments once
filled in. -->

# <Story title> — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task.
Each task = one commit unless noted. See `prompt.md` for why the story exists;
see `stories.md` for the per-task implementation spec.

**Open: <task ids>.**

<!-- Task-line format: one `- [ ]` per task, five `|`-separated fields. Owner/Model/Review
are filled now, at authoring time; SHA stays `—` until the task's commit lands, then set the
real SHA and tick the box.
  Owner:  who/what implements it — you, a named AI agent, or a named collaborator.
  Model:  the model id if Owner is an AI agent, else n/a.
  Review: the review gate this task needs — a named review step/agent, or "none" for
          docs-only work. Leave this project-specific; it is free text, not a fixed roster. -->

- [ ] **<ID-1>** — <what this task does> | Owner: <who> | Model: <model-id|n/a> | Review: <gate|none> | SHA: <—>
- [ ] **<ID-2>** — <what this task does> | Owner: <who> | Model: <model-id|n/a> | Review: <gate|none> | SHA: <—>

## Story done when

<!-- Acceptance criteria — prose, NO `- [ ]` / `- [x]` checkboxes. Per-task status lives only
in the working list above; this list is verified at story close. -->

- **<ID-1>** — <one-line done criterion>
- **<ID-2>** — <one-line done criterion>

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box.
Then update this story's status wherever it is summarised (a plan index file for a single
story, the epic `README.md` story list for an epic sub-story) and add one line to your
backlog/session-log file.
When the whole story is done, archive it per your project's own convention — do not leave a
done story half-archived.
