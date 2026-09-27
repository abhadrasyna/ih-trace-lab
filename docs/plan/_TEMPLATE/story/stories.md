<!-- Copy with the `story/` folder. Delete these HTML comments once filled in.
This file is the complete per-task implementation spec — a session should not need any
other planning doc to execute a task, only CONTEXT.md + the repo + your project's own
standards doc (AGENTS.md equivalent). -->

# <Story title> — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.
> Full implementation rules live in your project's own standards doc.
> After each task: set `SHA:` on the task line + tick the box, update the story status
> summary, add one line to your backlog/session-log file.

<!-- If this story changes persistent-storage schema: state here once, at the top —
"schema: use the exact definition in `schema.md`. Do not inline it below." -->

---

## <ID-1> — <title>

**Files to change / create:**
- `<path>` — <what changes>
- `<test path>` — <what it covers>

<!-- Optional — only if this project has a codebase knowledge graph or equivalent
structural-lookup tooling (Tier 3+). Delete this block entirely on a project that has no
such tooling; do not leave it as a dead step.
**Before any code (graph queries — do not write model constructors from memory):**
- look up the exact field list / required vs optional for any model you construct
- look up every enum member you reference
- trace callers/callees if the change ripples -->

**What to implement:**

1. <step>
2. <step>

**Tests (no network, no real external services):**
- `test_<happy_path>` — <assertion>
- `test_<edge_or_error>` — <assertion>

**Commit:** `<type>(<scope>): <subject ≤60 chars>`

---

## <ID-2> — <title>

<!-- same structure -->
