# Phase 0 automation prompt

> Paste the "Prompt to run" section below as your first message in a fresh Copilot CLI session, cwd `ih-trace-lab`. This file is the durable record of *why* each step exists; the prompt itself is
> self-contained and does not depend on reading this preamble.

## Background (why this file exists)

`docs/plan/TODOS.md` Phase 0 lists five independent, no-cross-dependency stories: `tenant-registry`, `project-taxonomy`, `functional-code-taxonomy`, `scratch-script-registry`,
`reference-knowledge-harvest`. Decided 2026-09-30, this session: automate all five via parallel Copilot CLI background agents, each running its story's tasks **unattended through completion** (not
pausing per task for review, since every task's commit stays independently revertible in git) — except where a task explicitly requires a human-only confirmation step, which cannot be faked by an
agent. Each agent works in its own `git worktree` to avoid five processes clobbering one shared working tree/git index. After each story's branch is reviewed and merged, run the `session-close` skill
scoped to that story before moving to the next.

## Prompt to run

```
You are automating docs/plan/TODOS.md's Phase 0 in ih-trace-lab. Read CONTEXT.md and AGENTS.md first, per this project's own protocol, and state "CONTEXT.md ✓".

Do the following, in order:

STEP 0 — Isolate each story in its own worktree (prevents 5 parallel agents from corrupting one shared git index/working tree):
  For each of these 5 stories, create a worktree + branch from the current main/default branch:
    - tenant-registry            -> ../wt-tenant-registry            (branch plan/tenant-registry)
    - project-taxonomy           -> ../wt-project-taxonomy            (branch plan/project-taxonomy)
    - functional-code-taxonomy   -> ../wt-functional-code-taxonomy    (branch plan/functional-code-taxonomy)
    - scratch-script-registry    -> ../wt-scratch-script-registry     (branch plan/scratch-script-registry)
    - reference-knowledge-harvest -> ../wt-reference-knowledge-harvest (branch plan/reference-knowledge-harvest)
  Use `git worktree add <path> -b <branch>` for each.

STEP 1 — Launch 5 background general-purpose agents in one batch. Give each agent this exact brief, substituting its own story/worktree:

    "Work in <worktree-path>. Read docs/plan/<story>/prompt.md, tasks.md, and stories.md. Work top-down through EVERY unchecked task in tasks.md, not just the first — this run is unattended,
    not paused for per-task review. For each task: implement exactly what stories.md specifies for that task id, run any tests it names, commit with one commit per task (message states the
    task id), then set that task's SHA on its tasks.md line and tick its checkbox, and update CONTEXT.md's bullet for this story if the task instructs that. Follow this project's AGENTS.md and
    CONTEXT.md conventions throughout.

    Stop early, before finishing all tasks, ONLY if: (a) a test fails and you cannot resolve it after a reasonable attempt, (b) a task's own spec requires a human-only confirmation step you
    cannot perform (tenant-registry's TR-1 is a known example: 'human confirms MCP query result matches expected opco' — a live Lightstep MCP call whose data-correctness only a human can judge),
    or (c) the task spec is genuinely ambiguous and guessing would risk silently-wrong output. If you stop early, report exactly which task and why, and leave every later task in that story
    unchecked and untouched.

    When done (or stopped early), report: which task ids you completed with their commit SHAs, which task id (if any) you stopped at and why, confirm no file under
    /Users/abhadra/github_copilot was touched, and include a self-summarized diff for this story — per completed task: files touched, line counts (+/-), and a one-line rationale. Do not
    paste raw diff hunks in this summary; I will pull the actual diff myself only for branches that need closer inspection."

STEP 2 — Wait for each agent's completion notification (do not poll). Read each agent's final report once it finishes or pauses.

STEP 3 — For each of the 5 branches, present me the agent's self-summarized diff (from its final report) as a consolidated per-story review — this replaces the normal per-task "human diff
  review" gate, since I've chosen a batched review for this run. Only pull the branch's actual `git log`/`git diff` on demand, for a specific branch I ask to inspect more closely — do not
  fetch full diffs for all 5 branches by default.

STEP 4 — After I approve a given branch (I may ask for fixes first — send those back to that story's agent via write_agent, do not start a new agent for the same story), merge that branch into
  main, remove its worktree (`git worktree remove`), and delete the branch.

STEP 5 — Immediately after merging each story's branch, invoke the `session-close` skill scoped to that story's just-merged work, before moving on to review the next branch's diff. Do this
  once per story, not once at the very end for all five.

STEP 6 — Once all 5 stories are either fully done or paused-with-a-clear-reason, update docs/plan/TODOS.md's Phase 0 checkboxes and add one line each to CONTEXT.md's "What Exists" bullets for
  any story that reached "done". Any story paused on a human-confirmation step (e.g. tenant-registry at TR-1) stays unchecked with a note on what input is needed to resume — do not mark it done.

Do not proceed past STEP 0 without first telling me the worktree/branch plan and getting my go-ahead, per this project's approval protocol.
```

## Notes for whoever runs this

- This intentionally trades the plan's default "review every task's diff before the next task starts" for "review once per story, at the end" — a deliberate choice made 2026-09-30, not a silent
  shortcut. If a story's later task turns out to depend on an earlier task's review feedback you would have given task-by-task, you'll only catch that at the consolidated review, and may need to send
  a follow-up fix to that story's (still-idle) agent rather than starting over.
- `tenant-registry` is expected to pause at TR-1 — that's correct behavior, not a bug. Its remaining tasks (TR-2..TR-6) resume only after you've confirmed the live MCP round-trip is opco-correct.
- Five agents write to five separate worktree directories, but they still share this machine's resources (CPU, any shared venv/test cache) — if runs seem to interfere, stagger launches instead of a
  single batch.
- STEP 3's review deliberately uses each agent's self-summarized diff, not raw `git diff` dumps, to avoid pulling ~5 branches' worth of full diff text into the orchestrating session's context. Fetch
  the actual diff only for a branch you decide needs closer inspection.
