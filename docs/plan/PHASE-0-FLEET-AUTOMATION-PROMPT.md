# Phase 0 fleet automation prompt (experimental — pilot first)

> This is a second, experimental automation design alongside `PHASE-0-AUTOMATION-PROMPT.md`. That file's manual `task`-agent-per-worktree approach is validated (pilot merged `375b73d`). This file
> swaps the manual "launch N background agents in one batch" orchestration for the CLI's native `/fleet` mode, while keeping worktree isolation and the human merge gate. **Not yet validated end to end
> — pilot the single-story prompt below before running the full batch.**

## Background (why this file exists, and what's unverified)

`/fleet` is the CLI's built-in pattern for dispatching multiple `task`-tool sub-agents in parallel, coordinated through a shared `todos`/`todo_deps` SQL state machine (`pending -> in_progress ->
done/blocked`). It maps well onto two things `PHASE-0-AUTOMATION-PROMPT.md` did by hand: (a) launching several stories' agents in one batch, and (b) STEP 4b's dependency (`reference-folder-diagrams`
waits on `functional-code-taxonomy`), which is exactly what `todo_deps` is designed to express.

Two things do NOT come for free from fleet and still need to be layered on top, same as the manual prompt:

1. **Worktree isolation.** Fleet runs sub-agents on the same filesystem; it does not isolate them into separate worktrees. Our stories share write targets (`TODOS.md`, `CONTEXT.md` in STEP 6), so each
   fleet todo's brief must still instruct the sub-agent to `git worktree add ../wt-<story> -b plan/<story>` as its first action, exactly as the manual prompt does.
2. **Human merge gate, and its interaction with fleet's dependency dispatch.** Fleet's documented default has a sub-agent self-mark `status = 'done'` on completion, which would immediately satisfy any
   dependency waiting on it — before a human has reviewed or merged anything. For `reference-folder-diagrams` this matters: it must wait until `functional-code-taxonomy` is **merged to main**, not
   merely until the sub-agent finishes its worktree. So each todo's brief must instruct the sub-agent to leave status at `in_progress` and report completion in its final message only; the
   orchestrating human (via the `sql` tool, in that fleet session) marks the todo `done` after reviewing the diff and merging. **This is a deviation from fleet's documented default behavior and is
   unverified — an LLM sub-agent could still self-mark done despite instructions.** The single-story pilot below cannot fully validate this specific point (nothing depends on `project-taxonomy`), so
   treat it as a known open risk until the full batch actually exercises the `functional-code-taxonomy` -> `reference-folder-diagrams` edge, and watch that transition closely when it happens.

## Pilot prompt (run this first, one story only)

> Paste this as your first message in a fresh Copilot CLI session, cwd `ih-trace-lab`.

```
Pilot the fleet+worktree automation design for exactly one Phase 0 story: project-taxonomy (no dependencies, no human-only MCP confirmation gate, unlike tenant-registry's TR-1).

Read CONTEXT.md and AGENTS.md first, per this project's protocol, and state "CONTEXT.md ✓" as the first line of your very first response.

STEP 0 — Run `git status --porcelain` on main; if it reports any output, stop and tell me before creating a worktree.

STEP 1 — Start /fleet with exactly one todo:
  id: project-taxonomy
  work item: "Work in a new worktree ../wt-project-taxonomy on branch plan/project-taxonomy (create it with `git worktree add` before any other action — never edit files in the main
    checkout directly). Read docs/plan/project-taxonomy/prompt.md, tasks.md, and stories.md. State 'CONTEXT.md ✓' as the first line of your very first response, before any other action.
    Work top-down through EVERY unchecked task in tasks.md, not just the first. For each task: implement exactly what stories.md specifies for that task id, run any tests it names, commit
    with one commit per task (message states the task id), then set that task's SHA on its tasks.md line and tick its checkbox, and update CONTEXT.md's bullet for this story if the task
    instructs that. Follow this project's AGENTS.md and CONTEXT.md conventions throughout. Stop early, before finishing all tasks, ONLY if a test fails and you cannot resolve it after a
    reasonable attempt, or a task spec is genuinely ambiguous and guessing would risk silently-wrong output — if so, report exactly which task and why, and leave every later task unchecked.
    When done (or stopped early), report: which task ids you completed with their commit SHAs, a self-summarized diff (files touched, line counts +/-, one-line rationale per task — do not
    paste raw diff hunks), and self-score this run against the AGENTS.md Tier 0 protocol checklist (CONTEXT.md read + stated first, scope/plan confirmed, tests written, CONTEXT.md updated if
    needed, tests green before commit, commit executed with SHA), flagging any step you skipped or deferred and why. Do NOT set this todo's status to 'done' yourself — leave it at
    'in_progress' and wait; I will mark it done myself after reviewing your report and merging."
  no dependencies for this pilot (single todo).

STEP 2 — Wait for the sub-agent's completion notification (do not poll). Read its final report once it finishes or pauses.

STEP 3 — Present me its self-summarized diff. I will approve, or send fixes back via write_agent to the same sub-agent (do not start a new one for the same story).

STEP 4 — After I approve, merge branch plan/project-taxonomy into main, remove the worktree (`git worktree remove ../wt-project-taxonomy`), delete the branch, and only then mark the
  project-taxonomy todo 'done' via the sql tool.

STEP 5 — Use the sub-agent's self-report from STEP 2/3 as the session-close-equivalent audit (file-based session-close cannot target a background agent's transcript — confirmed by the
  scratch-script-registry pilot). Record the self-scored checklist and any flagged deviations.

STEP 6 — Update docs/plan/TODOS.md's Phase 0 checkbox for project-taxonomy. Add a CONTEXT.md "What Exists" bullet ONLY if the story's own tasks did not already add one (check the merged
  diff first).

Do not proceed past STEP 0 without first telling me the worktree/branch plan and getting my go-ahead.

After all this, separately report: did /fleet's dispatch, worktree isolation, and the "don't self-mark done" instruction all work as described above? Flag anything that behaved differently
than expected — this is what I most need to know before scaling this design to the remaining stories.
```

## Full batch prompt (only after the pilot above passes)

Once the pilot confirms fleet dispatch, worktree isolation, and the withheld-done convention all behave as expected, repeat the same pattern for the remaining stories in one `/fleet` call with 4 todos
and one dependency edge: `functional-code-taxonomy` (`tenant-registry`, `reference-knowledge-harvest` have no dependencies), then a 5th todo `reference-folder-diagrams` with `depends_on:
functional-code-taxonomy`. Reuse the exact per-todo brief template from the pilot above (worktree-first, withheld-done, self-report + self-score), substituting each story's own name/worktree/branch.
Keep STEP 0/3/4/5/6 identical in spirit to `PHASE-0-AUTOMATION-PROMPT.md` — this file only changes STEP 1's dispatch mechanism from manual `task`-agent launches to `/fleet`, plus the mandatory
withheld-done handoff described above. `tenant-registry` is still expected to pause at TR-1 (human-only MCP confirmation) — that remains correct behavior, not a bug, regardless of dispatch mechanism.

## Notes for whoever runs this

- This file is deliberately separate from `PHASE-0-AUTOMATION-PROMPT.md`, not a replacement for it — until the pilot above passes, prefer the original manual prompt for real work.
- The withheld-done convention (STEP 4's "only mark done after merge") is the single highest-risk unverified assumption here. If the pilot or the later full batch shows a sub-agent self-marking done
  despite instructions, fall back to the manual `task`-agent design for the dependency-gated story (`reference-folder-diagrams`) rather than trusting fleet's dependency dispatch for it.
- Worktree isolation still has to be spelled out per-todo; fleet does not provide it automatically, and its own docs warn against using it where workers would contend for the same files — which is
  exactly our `TODOS.md`/`CONTEXT.md` situation without worktrees.
- Fleet sub-agents are dispatched the same way as the manual prompt's background `task` agents, so the confirmed cross-session-visibility limitation still applies: `list_agents`/`read_agent` from a
  *different* CLI session won't see them. Monitor via the worktree on disk (`git log`, `git status --short`, `tasks.md` checkboxes), the same method that worked throughout the original pilot.
