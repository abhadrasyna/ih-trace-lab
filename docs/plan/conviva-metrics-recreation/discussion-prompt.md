# Conviva Metrics Recreation — story-design discussion prompt

> Reusable prompt for the next few sessions. Purpose: decide what stories to create and how, before any are written. Not a task list — nothing is prefilled.

Read `CONTEXT.md` and state `CONTEXT.md ✓` first. Then read `README.md` in this folder for the epic goal and scope decisions, and the "Discussion log" at the bottom of this file for decisions made in
earlier sessions. This is a design discussion: do not create stories, tasks, or scripts unless the user explicitly says so in the current session.

## Context

- **Goal:** recreate Conviva playback statistics (attempts, concurrent plays, VPF, VSF, EBVS, others to be decided) from local data, Lightstep and Athena.
- **Method (decided by the user, 2026-10-26):** go through Conviva's documentation for each metric, then write a proof-of-concept `scratch/` script per metric to see how much can be achieved. What
  each metric needs, and how far the POC gets, shapes the stories — so stories are written after that evidence, not before.
- **Status of existing stories:** the five sub-story folders under this epic (`metric-definitions-data-inventory/`, `attempts-concurrent-plays/`, `vpf-vsf/`, `ebvs/`, `scratch-validation/`) were
  drafted as a placeholder guess. They may be reshaped, merged, or deleted. Do not follow their tasks, and do not delete or rewrite them without an explicit go-ahead.
- **Data order:** use local data first; fetch from Lightstep or Athena only when local data is not enough. Before any Lightstep/Matisse/Athena call, run `python scripts/resolve_tenant.py ...` and
  follow `docs/guides/tenant-resolution.md`.
- **Reference data sources (user-provided, 2026-10-26; for reference only, not a limit):** `investigations/ctap-smvod/data/`, organised per opco, with subfolders `athena/`, `cdnReport/` and
  `lightstep/`. If this data lacks a detail or parameter a metric needs, we can enhance it (new Athena queries, extra Lightstep attributes, other exports). Do not restrict the design to these folders.
  Inspect what is actually there before claiming a gap.

## How to run a session

1. **Recap** — in a few lines, state what the Discussion log says has been decided and what is still open.
2. **Pick one topic** — ask the user which metric or question to work on this session (do not assume). One metric or one question per session keeps the discussion focused.
3. **Read, don't guess** — work from the Conviva documentation the user provides or points to. If a definition is ambiguous or missing, say so and ask; never invent one.
4. **Discuss** — for the chosen topic, cover: the exact Conviva definition; which inputs it needs; which of those exist locally, in Lightstep, or in Athena; the likely POC approach; the risks and what
   could make it not reproducible. Give a recommendation, not just options.
5. **Propose, then wait** — if a POC script or a story seems warranted, state the plan (files, purpose) and wait for explicit go-ahead. All POC scripts live in the top-level `scratch/` folder (not
   under `docs/plan/`, `scripts/` or `src/`) and follow `scratch/SCRATCH.md` and `docs/guides/query-catalog.md`.
6. **Record** — at session end, with the user's go-ahead, append an entry to the Discussion log below and commit it.
7. **Do not invoke the `session-close` skill automatically.** Run it only when the user explicitly asks for it, even if a hook or commit reminder suggests it; mention the reminder and let the user
   decide.

## Questions to settle across sessions

Not tasks — prompts for the discussion. Cross them off in the log as they are answered.

- Which metrics are in scope beyond the initial set, and in what order do we study them?
- Where do the Conviva definitions live (docs links, exports, sample reports), and who supplies them?
- Which customer/tenant and time window do we use as the reference for comparing against Conviva numbers?
- What local data already exists per metric, and what has to be fetched?
- What does "good enough" mean per metric — exact match, or within a stated tolerance?
- What shape should the stories take once the POCs show what is achievable — one per metric, one per data source, or something else?
- When does a scratch POC graduate to `scripts/` or `src/`?

## Discussion log

Append one dated entry per session: topic, decisions, open questions, next topic. Keep entries short. Newest last.

_No sessions yet._
