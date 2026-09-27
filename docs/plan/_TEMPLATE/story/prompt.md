<!-- Copy the whole `story/` folder to docs/plan/<slug>/ (single story) or
docs/plan/<epic-slug>/<story-slug>/ (epic sub-story). <slug> is kebab-case: no date prefix,
no <slug>_ prefix on the files inside. Delete these HTML comments. -->

# <Story title> — prompt

> One-line statement of what this story delivers.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else.
Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task.
Read that task's full spec in `stories.md` (same task id) before writing any code.
One task per session. Complete it fully. Stop.

## Why this story exists

<!-- 1–3 short paragraphs. The problem, the trigger, the decision that scoped it. A reader
should understand why this exists without opening any other file. -->

## Scope guard

<!-- What this story does NOT touch. Name the modules / files in bounds and out of bounds.
State whether it changes runtime behaviour or is docs/tooling only. -->

## Session-start load hints

<!-- Which docs a session picking up this story must read beyond CONTEXT.md: other
reference docs, prior decisions, discussion output. Delete the ones that don't apply.
If this story changes persistent-storage schema, it carries a `schema.md` — name it here and
say "read it before any storage-layer work." -->

## Task overview

<!-- One line per task id in tasks.md, in order. The detail lives in stories.md. -->

## Definition of done

<!-- The whole-story completion bar. Mirrors `tasks.md` "## Story done when". Per-task DoD
goes in stories.md. -->

## Perspectives not covered

<!-- At least one thing this story's design doesn't address, so a reviewer knows what was
consciously left out rather than missed. Write "none identified" only if genuinely nothing
comes to mind. -->
