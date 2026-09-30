# Phase 0 SQL-tracked automation prompt (validated by the project-taxonomy pilot)

> Originally designed around the CLI's `/fleet` mode; the `project-taxonomy` pilot (2026-09-30) found `/fleet` is an interactive-mode UI toggle, not a callable tool that accepts a todos payload with a
> dependency graph — so this file has been renamed and corrected to document what the pilot actually exercised and confirmed working: the shared `todos`/`todo_deps` SQL tables for tracking (not
> automatic dispatch), `task(mode="background")` for launching each story's agent, worktree isolation, and a withheld-done handoff for the human merge gate. This is functionally the same dispatch
> mechanism as `PHASE-0-AUTOMATION-PROMPT.md`, with an added SQL-based status/dependency audit trail layered on top.

## Background (corrected from confirmed pilot findings)

**`/fleet` does not do what the earlier draft of this file assumed.** It is a slash-command UI toggle for an interactive multi-agent mode, not a programmatic orchestration primitive callable
mid-prompt with a todos/dependency-graph payload. There is no automatic "dependency edge satisfied -> dispatch next agent" engine to hand this off to. Confirmed by the pilot: when instructed to "start
/fleet with this todo," the agent substituted the `todos` SQL table (for status/dependency **tracking**) plus `task(mode="background")` (for actual **dispatch**) — this worked, but it means readiness
for a dependent story (`reference-folder-diagrams` waiting on `functional-code-taxonomy`) must be checked by a manual SQL query and a manual decision to launch, exactly as
`PHASE-0-AUTOMATION-PROMPT.md` already specified. There is no time or effort saved on the dependency-gating problem versus the original manual design — the value this file adds is a structured,
queryable status table instead of "watch the worktree on disk and remember where things stand."

**Confirmed working, keep these:**

1. **Worktree isolation** — `git worktree add ../wt-<story> -b plan/<story>` as the agent's first action worked exactly as designed: the agent's reads/writes/commits stayed fully isolated; `main` was
   untouched until the explicit merge step; `git worktree remove` + branch delete cleaned up with no residue.
2. **Withheld-done handoff** — the agent completed all its tasks, ticked its own task-level checkboxes in `tasks.md` (a separate, per-task checkbox it's supposed to manage), but correctly left the SQL
   `todos` row's status at `in_progress` and said so explicitly in its report. The orchestrating human flipped it to `done` only after reviewing the diff and merging. This is the part that matters for
   `reference-folder-diagrams`' dependency: querying `todo_deps` readiness only produces a correct answer if "done" means "merged," and this pilot confirms an agent will respect that instruction
   rather than self-marking done on task completion.
3. **SQL `todos` table as a cross-story status board** — worth keeping even without a dependency-auto-dispatch engine: `SELECT * FROM todos` gives one place to see every story's status
   (`pending`/`in_progress`/`done`/`blocked`) instead of checking each worktree individually. Seed one row per story up front (see below), and treat `todo_deps` rows as a readiness **reference**, not
   a trigger — the orchestrator runs the readiness query by hand before deciding to launch a dependent story's agent.

**New finding — resource/timing, factor into scaling to more stories:** the pilot's single story (8 tasks) took roughly 15 minutes wall-clock and 94+ tool calls. Running the 3 remaining Phase 0
stories (`tenant-registry`, `functional-code-taxonomy`, `reference-knowledge-harvest`) truly in parallel is plausible but multiplies visible tool-call volume/wall-clock contention correspondingly.
Decide up front whether to launch all 3 simultaneously or stage them (e.g. 2 at a time) before starting the full batch.

## Pilot outcome (recorded, not re-run)

`project-taxonomy` completed all 8 tasks (PT-1..PT-8), merged to `main`, worktree/branch removed, `TODOS.md` Phase 0 checkbox checked. Worktree isolation and the withheld-done handoff both worked as
designed (see above). The dependency-graph portion of the original design was never exercised (single todo, no deps) — treat `reference-folder-diagrams`' dependency edge as still unvalidated until the
full batch actually reaches that transition.

## Full batch prompt (remaining 3 Phase 0 stories + reference-folder-diagrams)

> Paste this as your first message in a fresh Copilot CLI session, cwd `ih-trace-lab`.

```
You are automating the remaining 3 Phase 0 stories (scratch-script-registry and project-taxonomy already landed via pilots) plus reference-folder-diagrams as a 4th, dependency-gated
story. Read CONTEXT.md and AGENTS.md first, and state "CONTEXT.md ✓" as the first line of your very first response.

STEP 0 — Run `git status --porcelain` on main; if it reports any output, stop and tell me before creating worktrees. Then tell me your worktree/branch plan and wait for my go-ahead
  before proceeding.

STEP 1 — Seed the sql tool's todos/todo_deps tables with one row per story: tenant-registry, functional-code-taxonomy, reference-knowledge-harvest, reference-folder-diagrams (status
  'pending' for all four). Insert one todo_deps row: reference-folder-diagrams depends_on functional-code-taxonomy. Decide with me now whether to launch the first 3 stories' agents
  simultaneously or staged (their combined tool-call volume was ~94+ per story in the pilot) before proceeding.

STEP 2 — For each of the 3 non-dependent stories, in the sequence we agreed in STEP 1: create its worktree (`git worktree add ../wt-<story> -b plan/<story>`), set its todo to
  'in_progress', and launch one background general-purpose agent with this brief (substitute the story name/worktree):

    "Work in <worktree-path>. Read docs/plan/<story>/prompt.md, tasks.md, and stories.md. State 'CONTEXT.md ✓' as the first line of your very first response, before any other action.
    Work top-down through EVERY unchecked task in tasks.md. For each task: implement exactly what stories.md specifies, run any tests it names, commit one commit per task (message states
    the task id), tick that task's tasks.md checkbox and record its SHA, and update CONTEXT.md's bullet for this story if the task instructs that. Follow this project's AGENTS.md and
    CONTEXT.md conventions throughout. Stop early ONLY if: (a) a test fails and you cannot resolve it after a reasonable attempt, (b) a task requires a human-only confirmation step you
    cannot perform (tenant-registry's TR-1: a live MCP query a human must judge for opco-correctness), or (c) the task spec is genuinely ambiguous. If you stop early, report exactly which
    task and why, and leave later tasks unchecked. When done or stopped, report: completed task ids with SHAs, a self-summarized diff (files touched, +/- line counts, one-line rationale
    per task, no raw diff hunks), and self-score this run against the AGENTS.md Tier 0 checklist, flagging any skipped/deferred step. Do NOT touch the sql todos table yourself — leave
    your story's row at 'in_progress'; the orchestrator marks it 'done' after reviewing your report and merging."

STEP 3 — Wait for each agent's completion notification (do not poll). Read each final report once it finishes or pauses.

STEP 4 — Present me each story's self-summarized diff as a consolidated per-story review. Only pull the branch's actual git log/diff on demand for a branch I ask to inspect more closely.

STEP 5 — After I approve a branch (or you relay my requested fixes to that story's still-idle agent via write_agent — never start a new agent for the same story), merge it into main,
  remove its worktree, delete its branch, and only then run `UPDATE todos SET status='done' WHERE id='<story>'` via the sql tool.

STEP 6 — As soon as functional-code-taxonomy's todo is 'done' (query todo_deps readiness by hand — there is no automatic trigger), create ../wt-reference-folder-diagrams on branch
  plan/reference-folder-diagrams and launch its agent with the same brief template, substituting reference-folder-diagrams as the story.

STEP 7 — Repeat STEP 3-5 for reference-folder-diagrams once its agent completes.

STEP 8 — Use each story's self-report as the session-close-equivalent audit (file-based session-close cannot target a background agent's transcript). Record the self-scored checklist and
  any flagged deviations per story, right after that story's merge — not once at the very end for all four.

STEP 9 — Once all 4 stories are either done or paused-with-a-clear-reason, update docs/plan/TODOS.md's Phase 0 checkboxes for the 3, and reference-folder-diagrams' own Phase 2 checkbox,
  separately. Add a CONTEXT.md "What Exists" bullet per story ONLY if its own tasks did not already add one (check the merged diff first). tenant-registry paused at TR-1 stays unchecked
  with a note on what input is needed to resume — do not mark it done.
```

## Notes for whoever runs this

- `tenant-registry` is expected to pause at TR-1 (human-only MCP confirmation) — correct behavior, not a bug.
- No automatic dependency-triggered dispatch exists in this environment; `reference-folder-diagrams`' launch in STEP 6 is a manual decision gated by a manual query, not something the runtime does for
  you. Don't assume future runs will auto-advance once a dependency's todo flips to `done`.
- The `todos` table's value here is a shared status board across stories, not automation — treat it as a lightweight audit/dashboard layer, same spirit as `TODOS.md` but queryable mid-run.
- Cross-session visibility limitation still applies: `list_agents`/`read_agent` from a *different* CLI session won't see these agents. Monitor via the worktree on disk, e.g.
  `scratch/2026-09-30_worktree_progress_monitor.py --worktree ../wt-<story> --tasks-file docs/plan/<story>/tasks.md --watch --interval 300`.
- Decide staged vs. parallel launch for the 3 non-dependent stories up front (STEP 1) based on the pilot's ~15min/~94-tool-call-per-story cost — don't default to "launch all 3 at once" without
  considering that multiplier.
