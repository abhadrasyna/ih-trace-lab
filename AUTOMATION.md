# AUTOMATION.md

> How to run a multi-story `docs/plan/` epic ("autopilot") in one sitting without repeating the `src-lib-migration` 2026-10-02 run's problems. That run executed all 6 stories (24 task segments) inside
> one single-agent session with no re-check between segments — it produced the highest-ranked rows in `suggestions.md` (`re-read-context-on-resumed-task-segments`, `state-plan-before-editing`,
> `wait-for-explicit-go-ahead-before-editing`, `avoid-mid-session-rereads`) and avoidable `output_discipline_flags`, all visible per-segment in `session_audit.jsonl`. The epic's own code landed
> correctly; the cost was process, not correctness — token spend and protocol drift that compounded with every added segment.

## Why sub-agents, not one long session

A single agent session accumulates every prior story's transcript in context — by story 5 of 6, re-reading `CONTEXT.md`, the epic `README.md`, or a sibling story's `stories.md` is reading content
already paid for once already. `docs/plan/`'s own story-folder convention (`prompt.md` + `tasks.md` + `stories.md`, independently scoped, each with its own first-unchecked-task) already draws the
boundary an autopilot run should delegate along: **one sub-agent per story**, not one agent for the whole epic.

- Each sub-agent reads only: the epic's `README.md` (shared brief, once), its own story's `prompt.md`/`tasks.md`/`stories.md`, and `CONTEXT.md`. Nothing from a sibling story's working context.
- Each sub-agent's first turn satisfies `AGENTS.md` Steps 1-3 fresh — there is no "resumed segment" to silently skip the plan/go-ahead check on, because there is no mid-session resumption at all.
- Token cost scales with the epic's story count, not with the epic's story count *squared* (no re-paying for stories 1..N-1's context on story N).

## Recommended run shape

1. **Confirm scope once, at the epic level**, before launching anything: which stories, in what order (respecting the epic's own `Depends on` column), and whether the user wants to approve each
   story's result before the next one starts, or batch-review at the end. Do not assume — this is exactly the kind of judgment call `AGENTS.md` Step 2 requires asking about.
2. **Launch one sub-agent per story**, in dependency order (a story blocked on a sibling's output must wait for that sibling to finish; independent stories may run in parallel). Give each sub-agent a
   complete, self-contained prompt: the story's slug and folder path, its first unchecked task id, the epic's `Depends on` constraint if any, and an explicit instruction to follow this repo's own
   `AGENTS.md` protocol (read `CONTEXT.md`, state the plan, wait for go-ahead if the harness requires it, write tests, commit, update `CONTEXT.md`). Sub-agent prompts are not subject to the brevity
   rules the top-level session's replies are — give them full context once, not a terse pointer that forces a re-derivation.
3. **Let each sub-agent complete and commit its own story** before starting the next dependent one. A story's own `tasks.md` is the sub-agent's checklist; the top-level session's job is orchestration
   (launch, collect result, confirm the commit SHA, move to the next story), not re-doing the sub-agent's reads.
4. **Update the epic `README.md`'s Stories table once per completed story** (status + closing SHA), from the top-level session, after each sub-agent finishes — this is the one piece of epic-level
   bookkeeping that must not be delegated per-story, since it is the cross-story shared state.
5. **Archive the epic** with `scripts/dev/archive_completed_story.py <epic-slug>` once every sub-story shows `**Open: none — story complete.**`, same as any other story (see `docs/plan/README.md`).

## Token-efficiency rules specific to autopilot runs

- Never re-read a file (e.g. `CONTEXT.md`, the epic `README.md`) in the top-level orchestrating session once its content is already in context from an earlier turn in the same session, unless it
  changed. Delegate the *read* to the sub-agent instead of re-reading it yourself just to construct the sub-agent's prompt — pass the file path, not a re-quoted dump of its contents. Note: this does
  not apply across different sub-agents; each sub-agent's own isolated context has no prior exposure to that file and must read it once itself as part of its own Step 1.
- Use scoped reads (`view_range`, `grep`) in the orchestrating session for anything beyond confirming a sub-agent's result (e.g. checking the new commit SHA, the updated `tasks.md` checkbox) — never a
  full-file dump to "double check" something a sub-agent already reported.
- A sub-agent's full output does not need to be echoed back to the user turn-by-turn; summarize what changed (files, commit SHA, test result) and move to the next story.

## The backstop, if autopilot is run as one session anyway

If a genuine constraint (e.g. no sub-agent delegation available in a given context) forces running an epic as task segments inside one session, `scripts/dev/hooks/autopilot_checkpoint.py` (registered
via `.github/hooks/autopilot-checkpoint.json`) forces a plan/go-ahead checkpoint every 5 agent turns regardless of whether a commit has landed — unlike `scripts/dev/hooks/session_close_on_commit.py`,
which only fires on a new commit, and `.github/hooks/session-context.json`, which only fires once at `sessionStart`. This is strictly a fallback: it catches drift after the fact, every 5 turns, rather
than preventing it the way per-story sub-agent isolation does from the start. Prefer the sub-agent shape above whenever it is available.
