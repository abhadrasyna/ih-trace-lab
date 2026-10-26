# Conviva Metrics Recreation — story-design discussion prompt

> Reusable prompt for the next few sessions. Purpose: decide what stories to create and how, from POC evidence. Not a task list; the Discussion log at the bottom holds what has been decided so far
> (attempts is done through the chart; no other metric has been studied yet).

Read `CONTEXT.md` and state `CONTEXT.md ✓` first. Then read `README.md` in this folder for the epic goal and scope decisions, and the "Discussion log" at the bottom of this file for decisions made in
earlier sessions. This is a design discussion: do not create stories, tasks, or scripts unless the user explicitly says so in the current session.

## Context

- **Goal:** recreate Conviva playback statistics (attempts, concurrent plays, VPF, VSF, EBVS, others to be decided) from local data, Lightstep and Athena.
- **Method (decided by the user, 2026-10-26):** go through Conviva's documentation for each metric, then write a proof-of-concept `scratch/` script per metric to see how much can be achieved. What
  each metric needs, and how far the POC gets, shapes the stories — so stories are written after that evidence, not before.
- **Status of existing stories (updated 2026-10-26):** `attempts/` is the first story written from POC evidence (see the log) and is in progress; its tasks CMR-ATT-1 to CMR-ATT-3 are done and
  CMR-ATT-4 to CMR-ATT-7 are open. The other five sub-story folders (`metric-definitions-data-inventory/`, `attempts-concurrent-plays/`, `vpf-vsf/`, `ebvs/`, `scratch-validation/`) are still the
  placeholder guess. They may be reshaped, merged, or deleted. Do not follow their tasks, and do not delete or rewrite them without an explicit go-ahead. `attempts-concurrent-plays/` is left as is and
  now covers concurrent plays only.
- **Data order:** use local data first; fetch from Lightstep or Athena only when local data is not enough. Before any Lightstep/Matisse/Athena call, run `python scripts/resolve_tenant.py ...` and
  follow `docs/guides/tenant-resolution.md`.
- **Reference data sources (user-provided, 2026-10-26; for reference only, not a limit):** `investigations/ctap-smvod/data/`, organised per opco, with subfolders `athena/`, `cdnReport/` and
  `lightstep/`. If this data lacks a detail or parameter a metric needs, we can enhance it (new Athena queries, extra Lightstep attributes, other exports). Do not restrict the design to these folders.
  Inspect what is actually there before claiming a gap.
- **POC scope (user-decided, 2026-10-26):** the POC runs for a single day, 24 October (2026-10-24, confirm the year with the user at session start), and a single tenant, ZA. Resolve the ZA tenant id
  via `scripts/resolve_tenant.py`; never guess it.
- **Generic by design:** the POC is narrow, but everything written from it must be generic. Stories, definitions and scripts must be opco/tenant-agnostic and date-agnostic: tenant and date are
  arguments (argparse), never hardcoded, and nothing may depend on ZA-specific fields without that being a documented, parameterised mapping. When a ZA finding might not hold for other opcos, record
  it as an assumption to verify, and extrapolate the design so the story can be run for any tenant and date.

## How to run a session

1. **Recap** — in a few lines, state what the Discussion log says has been decided and what is still open.
2. **Pick one topic** — ask the user which metric or question to work on this session (do not assume). One metric or one question per session keeps the discussion focused.
3. **Understand the definition** — work from the Conviva documentation the user provides or points to. If a definition is ambiguous or missing, say so and ask; never invent one.
4. **Check local sources** — look in `investigations/ctap-smvod/data/` and other local data for the ZA tenant on 2026-10-24: can the metric be regenerated from what is already held? State which inputs
   are present and which are missing.
5. **Fetch the missing links** — only for inputs not available locally, query Lightstep or Athena (after tenant resolution), scoped to ZA and 2026-10-24. Save what is fetched where later sessions can
   reuse it, and say what was added.
6. **Discuss** — for the chosen topic, cover: the definition; the inputs and where each comes from; the likely POC approach; what would make it not reproducible; and how it generalises to other opcos
   and dates. Give a recommendation, not just options. For charts, follow `docs/guides/chart-guidelines.md` and reuse `scratch/_lib/line_chart.py` (`render_line`) before writing a new renderer.
7. **Propose, then wait** — if a POC script or a story seems warranted, state the plan (files, purpose) and wait for explicit go-ahead. All POC scripts live in the top-level `scratch/` folder (not
   under `docs/plan/`, `scripts/` or `src/`) and follow `scratch/SCRATCH.md` and `docs/guides/query-catalog.md`.
8. **Record** — at session end, with the user's go-ahead, append an entry to the Discussion log below and commit it.
9. **Do not invoke the `session-close` skill automatically.** Run it only when the user explicitly asks for it, even if a hook or commit reminder suggests it; mention the reminder and let the user
   decide.

## Questions to settle across sessions

Not tasks — prompts for the discussion. Cross them off in the log as they are answered.

- Which metrics are in scope beyond the initial set, and in what order do we study them? _Partly answered: attempts studied first (2026-10-26); order for the rest still open._
- Where do the Conviva definitions live (docs links, exports, sample reports), and who supplies them? _Partly answered: docs.conviva.ai metric dictionary pages, supplied by the user per metric. The
  formula images on those pages are not readable by us; ask the user for them._
- Which customer/tenant and time window do we use as the reference for comparing against Conviva numbers? _Answered for the POC: ZA, 2026-10-24. Still open: a Conviva reference number for that day._
- What local data already exists per metric, and what has to be fetched? _Answered for attempts: local Athena `debug_states` is enough for the count; the gaps to other sources are open (CMR-ATT-4)._
- What does "good enough" mean per metric — exact match, or within a stated tolerance?
- What shape should the stories take once the POCs show what is achievable — one per metric, one per data source, or something else? _Provisional: one story per metric (`attempts/` as the pattern:
  done POC tasks, open gap/definition/generalisation tasks, a graduation task)._
- When does a scratch POC graduate to `scripts/` or `src/`? _Provisional: after its gaps are explained and it runs for a second tenant and date, with the user's separate go-ahead (CMR-ATT-7)._

## Discussion log

Append one dated entry per session: topic, decisions, open questions, next topic. Keep entries short. Newest last.

### 2026-10-26 — Attempts (first topic)

- **Decided:** attempts uses the Conviva definition "sum of all attempts"; the summary equals the sum of the time-series points. POC on ZA, 2026-10-24 (the year was never explicitly confirmed; the
  user's data and approval used it), local Athena `debug_states` only, one attempt per distinct `sessionId` with a CREATE event, UTC buckets, 5-minute default. Chart finalised: title, large KPI under
  it, metadata footer, plain line with flat fill (a moving-average variant was rejected). Story `attempts/` created; the placeholder `attempts-concurrent-plays/` is untouched.
- **Result:** 3,901 attempts. Other sources: `session.csv` 3,797, `outcome_first_debug` 3,808, Lightstep smvod 4,443.
- **Open:** the 138-140 CREATE sessions missing from the Athena exports and the extra Lightstep sessions; the Conviva formula image and a reference number; UTC versus local day; auto-play and revived
  sessions; running for another tenant and date; graduation of the POC and `scratch/_lib/line_chart.py`.
- **Next topic:** ask the user (gap investigation for attempts, or the next metric).
