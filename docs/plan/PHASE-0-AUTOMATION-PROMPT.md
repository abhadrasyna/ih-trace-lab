# Phase 0 automation prompt

> Paste the "Prompt to run" section below as your first message in a fresh Copilot CLI session, cwd `ih-trace-lab`. This file is the durable record of *why* each step exists; the prompt itself is
> self-contained and does not depend on reading this preamble.

## Background (why this file exists)

`docs/plan/TODOS.md` Phase 0 lists five independent, no-cross-dependency stories: `tenant-registry`, `project-taxonomy`, `functional-code-taxonomy`, `scratch-script-registry`,
`reference-knowledge-harvest`. Decided 2026-09-30, this session: automate them all via parallel Copilot CLI background agents, each running its story's tasks **unattended through completion** (not
pausing per task for review, since every task's commit stays independently revertible in git) — except where a task explicitly requires a human-only confirmation step, which cannot be faked by an
agent. Each agent works in its own `git worktree` to avoid parallel processes clobbering one shared working tree/git index.

`scratch-script-registry` was run first as a single-story pilot (2026-09-30, merged `375b73d`) to validate this approach before committing to the remaining four in parallel. The pilot confirmed
background `task` agents do not get a discoverable per-agent transcript file, so file-based `session-close` cannot audit them — the remaining stories below use an agent self-report + self-scoring
mechanism instead (see STEP 1/5). The pilot also found the agent stated "CONTEXT.md ✓" only in its final report rather than its first response, now fixed in STEP 1's brief.

`reference-folder-diagrams` (Phase 2 per `TODOS.md`) is added to this batch as a 5th story, 2026-09-30: its own stated blocker — `reference-code-gap-migration`'s GAP-1 decisions — is confirmed closed,
and `TODOS.md` itself already recommends doing it early so its diagrams can inform the migration epics rather than just document them after the fact. It is docs/tooling-only (never touches `src/`,
`investigations/`, or `github_copilot`) and has no human-confirmation gates (`RFD-1`: `py-code-review` hook; `RFD-2`..`RFD-10`: no review). It is NOT launched in the initial parallel batch, because
its session-start hints cite `functional-code-taxonomy`'s target `src/lib/*` module map for RFD-6/RFD-7 — it is launched only after `functional-code-taxonomy` has merged (see STEP 4b/5b), so its
diagrams cite that module map's final, merged form rather than a version that could still change mid-batch.

## Prompt to run

```
You are automating the remaining 4 stories of docs/plan/TODOS.md's Phase 0 in ih-trace-lab (`scratch-script-registry` already landed via a pilot run, merged `375b73d`), plus
`reference-folder-diagrams` (Phase 2, added to this batch — see Background) as a 5th story that starts once `functional-code-taxonomy` merges. Read CONTEXT.md and AGENTS.md first, per this
project's own protocol, and state "CONTEXT.md ✓" as the first line of your very first response — not deferred to a later or final report.

Do the following, in order:

STEP 0 — Verify a clean starting point, then isolate each of the 4 initial stories in its own worktree (prevents parallel agents from corrupting one shared git index/working tree):
  Run `git status --porcelain` on main; if it reports any output, stop and tell me before creating worktrees (do not stash/discard on my behalf).
  For each of these 4 stories, create a worktree + branch from the current main/default branch:
    - tenant-registry            -> ../wt-tenant-registry            (branch plan/tenant-registry)
    - project-taxonomy           -> ../wt-project-taxonomy            (branch plan/project-taxonomy)
    - functional-code-taxonomy   -> ../wt-functional-code-taxonomy    (branch plan/functional-code-taxonomy)
    - reference-knowledge-harvest -> ../wt-reference-knowledge-harvest (branch plan/reference-knowledge-harvest)
  Use `git worktree add <path> -b <branch>` for each. `reference-folder-diagrams`' worktree is created later, in STEP 4b, once `functional-code-taxonomy` has merged.

STEP 1 — Launch 4 background general-purpose agents in one batch. Give each agent this exact brief, substituting its own story/worktree. The pilot run (`scratch-script-registry`, 2026-09-30)
  confirmed background `task` agents do NOT get their own discoverable `session-state/<id>/events.jsonl` — their activity is embedded in the orchestrator's own transcript. Per-story file-based
  `session-close` (as originally designed) is not possible; STEP 5 below uses the agent's own self-report instead:

    "Work in <worktree-path>. Read docs/plan/<story>/prompt.md, tasks.md, and stories.md. State 'CONTEXT.md ✓' as the first line of your very first response, before any other action. Work
    top-down through EVERY unchecked task in tasks.md, not just the first — this run is unattended, not paused for per-task review. For each task: implement exactly what stories.md specifies
    for that task id, run any tests it names, commit with one commit per task (message states the task id), then set that task's SHA on its tasks.md line and tick its checkbox, and update
    CONTEXT.md's bullet for this story if the task instructs that. Follow this project's AGENTS.md and CONTEXT.md conventions throughout.

    Stop early, before finishing all tasks, ONLY if: (a) a test fails and you cannot resolve it after a reasonable attempt, (b) a task's own spec requires a human-only confirmation step you
    cannot perform (tenant-registry's TR-1 is a known example: 'human confirms MCP query result matches expected opco' — a live Lightstep MCP call whose data-correctness only a human can judge),
    or (c) the task spec is genuinely ambiguous and guessing would risk silently-wrong output. If you stop early, report exactly which task and why, and leave every later task in that story
    unchecked and untouched.

    When done (or stopped early), report: which task ids you completed with their commit SHAs, which task id (if any) you stopped at and why, confirm no file under
    /Users/abhadra/github_copilot was touched, include a self-summarized diff for this story — per completed task: files touched, line counts (+/-), and a one-line rationale (do not paste raw
    diff hunks; I will pull the actual diff myself only for branches that need closer inspection) — and additionally self-score this run against the AGENTS.md Tier 0 protocol checklist (CONTEXT.md
    read + stated first, scope/plan confirmed, tests written, CONTEXT.md updated if needed, tests green before commit, commit executed with SHA), flagging any step you skipped or deferred and why."

STEP 2 — Wait for each agent's completion notification (do not poll). Read each agent's final report once it finishes or pauses.

STEP 3 — For each of the 4 branches, present me the agent's self-summarized diff (from its final report) as a consolidated per-story review — this replaces the normal per-task "human diff
  review" gate, since I've chosen a batched review for this run. Only pull the branch's actual `git log`/`git diff` on demand, for a specific branch I ask to inspect more closely — do not
  fetch full diffs for all 4 branches by default.

STEP 4 — After I approve a given branch (I may ask for fixes first — send those back to that story's agent via write_agent, do not start a new agent for the same story), merge that branch into
  main, remove its worktree (`git worktree remove`), and delete the branch.

STEP 4b — As soon as `functional-code-taxonomy` specifically has been merged (regardless of whether the other 3 are done yet), create its worktree + branch and launch its agent:
  `git worktree add ../wt-reference-folder-diagrams -b plan/reference-folder-diagrams`. Launch one background general-purpose agent with the same brief template as STEP 1, substituting
  `reference-folder-diagrams` as the story and `../wt-reference-folder-diagrams` as the worktree — including the same stop conditions, self-summarized-diff, and self-scoring requirements.

STEP 5 — Immediately after merging each story's branch (including `reference-folder-diagrams`, once STEP 4b's agent completes and its branch is approved/merged), use the agent's own self-report
  (from STEP 2/3, or STEP 4b's equivalent report) as the `session-close`-equivalent audit for that story — file-based `session-close` cannot target a background agent's transcript (see STEP 1
  finding), so this replaces it, not supplements it. Record the self-scored protocol checklist and any flagged deviations in your consolidated review for that story before moving on to review
  the next branch's diff. Do this once per story, not once at the very end for all five.

STEP 6 — Once all 5 stories (the original 4 plus `reference-folder-diagrams`) are either fully done or paused-with-a-clear-reason, update docs/plan/TODOS.md's Phase 0 checkboxes for the 4, and
  `reference-folder-diagrams`' own Phase 2 checkbox, separately. For each story that reached "done", add a "What Exists" bullet to CONTEXT.md ONLY if that story's own tasks did not already
  add/update one during merge (check the merged diff first — do not duplicate an edit the story's own commits already made; the pilot's own STEP 6 needed no further edit for exactly this
  reason). Any story paused on a human-confirmation step (e.g. tenant-registry at TR-1) stays unchecked with a note on what input is needed to resume — do not mark it done.

Do not proceed past STEP 0 without first telling me the worktree/branch plan and getting my go-ahead, per this project's approval protocol.
```

## Notes for whoever runs this

- This intentionally trades the plan's default "review every task's diff before the next task starts" for "review once per story, at the end" — a deliberate choice made 2026-09-30, not a silent
  shortcut. If a story's later task turns out to depend on an earlier task's review feedback you would have given task-by-task, you'll only catch that at the consolidated review, and may need to send
  a follow-up fix to that story's (still-idle) agent rather than starting over.
- `tenant-registry` is expected to pause at TR-1 — that's correct behavior, not a bug. Its remaining tasks (TR-2..TR-6) resume only after you've confirmed the live MCP round-trip is opco-correct.
- Agents write to separate worktree directories, but they still share this machine's resources (CPU, any shared venv/test cache) — if runs seem to interfere, stagger launches instead of a single
  batch.
- STEP 3's review deliberately uses each agent's self-summarized diff, not raw `git diff` dumps, to avoid pulling several branches' worth of full diff text into the orchestrating session's context.
  Fetch the actual diff only for a branch you decide needs closer inspection.
- **Confirmed by the `scratch-script-registry` pilot (2026-09-30, merged `375b73d`):** background `task` agents do not persist a discoverable transcript under their `agent_id` — their tool calls and
  turns are embedded in the orchestrating session's own `events.jsonl`, not a separate file. File-based `session-close` (STEP 1's original design) cannot target a specific background agent's work, so
  it is not used for these stories. STEP 1/5's self-report + self-scoring mechanism (agent restates its own protocol-checklist compliance in its final report) is the working replacement. This also
  means the orchestrating session's own transcript mixes all stories' turns — if a full transcript-based audit is ever needed later, it would have to be scoped by timestamp/task-id within that one
  shared file, not by a separate per-story file.
- **Also confirmed by the pilot:** the agent stated "CONTEXT.md ✓" only in its final report, not its first response, technically satisfying the letter of AGENTS.md's instruction late rather than up
  front. STEP 1's brief now explicitly requires it as the first line of the agent's first response.
- **`reference-folder-diagrams` is deliberately deferred to STEP 4b, not launched in the initial parallel batch:** its RFD-6/RFD-7 diagrams cite `functional-code-taxonomy`'s target `src/lib/*` module
  map. Launching it in parallel with `functional-code-taxonomy` risks it citing a module-map version that later changes before `functional-code-taxonomy` actually merges — waiting for that merge first
  removes the risk cheaply, at the cost of `reference-folder-diagrams` starting a bit later than the other 4.
