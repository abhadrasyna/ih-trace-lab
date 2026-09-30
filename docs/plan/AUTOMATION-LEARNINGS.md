# Parallel background-agent automation — learnings

> A durable reference for running Copilot CLI background agents in parallel (git-worktree-isolated, human-gated merges) on any future batch of independent stories — not just Phase 0. Read this before
> designing the next such batch; it distills what actually held up versus what turned out to be wrong assumptions, across the `scratch-script-registry`, `project-taxonomy`, and
> `reference-folder-diagrams`-planning work in 2026-09-30's session. See `PHASE-0-AUTOMATION-PROMPT.md` and `PHASE-0-SQL-TRACKED-AUTOMATION-PROMPT.md` for the runnable templates this distills from.

## Core mechanism (confirmed working, twice)

- Each story's agent works in its own `git worktree` (`git worktree add ../wt-<story> -b plan/<story>`), never the main checkout. This is what actually prevents parallel agents from corrupting one
  shared working tree/index, and it worked cleanly both times: no cross-story file contention, no residue after `git worktree remove` + branch delete.
- Dispatch is a background `task`/`general-purpose` agent per story, given a self-contained brief (read `prompt.md`/`tasks.md`/`stories.md`, work top-down through every unchecked task, one commit per
  task, stop only on defined conditions, report a self-summarized diff).
- Human review happens once per story at the end (a consolidated self-summarized diff), not once per task — a deliberate tradeoff, not a shortcut: if a later task depended on feedback you'd have given
  earlier, you only catch it at the consolidated review and may need a follow-up fix sent to the (still-idle) agent via `write_agent`, rather than restarting.

## Confirmed limitations (do not re-assume these work differently)

- **`list_agents`/`read_agent` only see agents in the *current* CLI session.** A background agent launched in a different session (or by the user directly pasting a prompt elsewhere) is invisible to
  these tools. The only reliable cross-session monitoring method is inspecting the worktree directly on disk: `git log`, `git status --short`, grepping `tasks.md` checkboxes. Automated via
  `scratch/2026-09-30_worktree_progress_monitor.py --worktree <path> --tasks-file <path> --watch --interval <seconds>`.
- **Background `task` agents do not get a discoverable per-agent transcript.** There is no separate `session-state/<agent_id>/events.jsonl` — their activity is embedded in the orchestrating session's
  own transcript. File-based `session-close` (resolving a transcript by session folder) cannot audit a specific background agent's work. Replacement: have the agent self-report and self-score against
  the `AGENTS.md` Tier 0 checklist (CONTEXT.md read + stated first, scope confirmed, tests written, CONTEXT.md updated, tests green, commit executed with SHA) inline in its final message; record that
  as the audit.
- **`/fleet` is an interactive-mode UI toggle, not a callable orchestration tool.** It does not accept a todos/dependency-graph payload from within a prompt, and there is no automatic "dependency
  satisfied -> dispatch next agent" engine to rely on. If a batch has a real dependency between stories (one must merge before the next starts), that has to be a manual step: query readiness by hand
  (e.g. against the `sql` tool's `todos`/`todo_deps` tables, used as a status board) and manually launch the dependent story's agent once satisfied.
- **An agent will state a required first-line instruction (e.g. `"CONTEXT.md ✓"`) only in its *final* report unless the brief explicitly says "as the first line of your very first response."** Late
  compliance is a real, observed deviation — spell out timing explicitly for anything that must happen early, not just that it must happen.
- **An agent will respect an explicit "do not self-mark done" instruction.** Confirmed: when told to leave a shared status row (SQL `todos.status`) at `in_progress` and let the human flip it to `done`
  only after merge, the agent did exactly that and said so in its report. This is the mechanism to use for any dependency-gating that needs "done" to mean "merged to main," not "worktree work
  finished."

## Practical gotchas worth avoiding next time

- **Two different markdown line-length mechanisms behave differently on fenced code blocks.** `scripts/dev/reflow_md.py --check` can report "already in fill-to-≤200 style" while the actual pre-commit
  hook (`scripts/dev/hooks/check_md_line_length.py`) still fails on long lines *inside* a fenced code block — the reflow tool doesn't touch fenced content, the hook does. Always run both directly on a
  prompt file with an embedded code-fenced prompt before assuming it's commit-ready.
- **The `edit` tool's `old_str` matching is fragile against files that were just reflowed** — a reflow pass changes line-wrap points, so a large multi-paragraph `old_str` written against the
  pre-reflow text can fail to match. Falling back to `create` (full-file rewrite) is sometimes faster than chasing exact whitespace.
- **Resource/timing data point**: one 8-task story (`project-taxonomy`) took roughly 15 minutes wall-clock and 94+ tool calls end to end. Running several stories' agents truly in parallel multiplies
  visible tool-call volume and wall-clock contention correspondingly — decide staged vs. simultaneous launch up front for a multi-story batch rather than defaulting to "launch everything at once."

## Recommended process for the next parallel batch

1. Pilot with exactly one story first (pick one with no dependencies and no human-only confirmation gate) before committing to the full batch — this is how both confirmed-working mechanisms above were
   actually validated, and how the `/fleet` false assumption was caught before it wasted a multi-story run.
2. Write the per-story agent brief once, explicitly including: worktree-first instruction, "CONTEXT.md ✓ as the first line of your very first response," the task-by-task commit convention, defined
   stop conditions (unresolved test failure, human-only confirmation step, genuine ambiguity), and the self-summarized-diff + self-score report format.
3. If any story depends on another, model it as a manual gate: merge the prerequisite, review it, then manually launch the dependent story's agent — don't design around an auto-dispatch mechanism that
   doesn't exist in this environment.
4. Review once per story (consolidated self-summarized diff), pulling the real `git diff`/`git log` only for a branch that needs closer inspection.
5. Update `TODOS.md`/`CONTEXT.md` per story only if the story's own commits didn't already do it — check the merged diff first to avoid a duplicate edit.
