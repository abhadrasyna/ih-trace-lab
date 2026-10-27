# Conviva Metrics Recreation — story-design discussion prompt

> Reusable prompt for the next few sessions. Purpose: decide what stories to create and how, from POC evidence. Not a task list; the Discussion log at the bottom holds what has been decided so far
> (attempts POC is done: chart and supporting report; no other metric has been studied yet).

Read `CONTEXT.md` and state `CONTEXT.md ✓` first. Then read `README.md` in this folder for the epic goal and scope decisions, and the "Discussion log" at the bottom of this file for decisions made in
earlier sessions. This is a design discussion: do not create stories, tasks, or scripts unless the user explicitly says so in the current session.

## Required flow (every metric, in this order)

The scratch POC is **not a deliverable**. It is the way we learn enough to write the story. In the attempts work the story and tasks were first written as if the POC were the deliverable and had to be
recreated; do not repeat that. Run the steps in order, and stop for the user's explicit go-ahead at each transition.

1. **Learn the metric from Conviva** — work from the documentation the user supplies (docs.conviva.ai metric dictionary). Record the definition, counting rule, bucket and timezone. If a definition is
   ambiguous or the formula image is unreadable, ask; never invent one.
2. **Check local data** — look in `investigations/ctap-smvod/data/` and other local data first. State which inputs are present, which are missing, and whether the metric can be derived from them.
3. **Fetch what is missing** — only for gaps, query Lightstep (new trace data) or Athena (after `python scripts/resolve_tenant.py ...` and `docs/guides/tenant-resolution.md`). Save what is fetched
   where later sessions can reuse it, and say what was added.
4. **Produce a graph and a markdown summary per metric** — one chart and one analysis report for each metric (see "Deliverable pattern"). Steps 2-4 run in a single script under the top-level
   `scratch/`, following `scratch/SCRATCH.md` and `docs/guides/query-catalog.md`.
5. **Finalise the output** — the user reviews the graph and the markdown. Iterate in scratch until both are accepted (attempts went through several chart revisions). Nothing is formalised before this.
6. **Create the story from the finalised output** — only with the user's go-ahead, and using `docs/refactor/` (especially `planning-protocol.md`, `design-principles.md` and
   `code-deduplication-and-taxonomy.md`) and the design guidelines in `docs/guides/` (`project-taxonomy.md`, `functional-code-taxonomy.md`). The accepted graph and report are the specification; the
   POC code is reference only and is retired afterwards. Tasks describe the formal build, not the POC.
7. **Epic outcome** — once the POCs are finalised, the epic produces a complete `investigations/<slug>/` folder (docs, scripts, outputs, retention per `docs/guides/project-taxonomy.md`) with the
   required code. Anything specific to one investigation goes in its scripts; every common functionality goes in `src/lib/`. Where a piece lives depends on how it is used.

## Context

- **Goal:** recreate Conviva playback statistics (attempts, concurrent plays, VPF, VSF, EBVS, others to be decided) from local data, Lightstep and Athena.
- **Method (decided by the user, 2026-10-26):** go through Conviva's documentation for each metric, then write a proof-of-concept `scratch/` script per metric to see how much can be achieved. What
  each metric needs, and how far the POC gets, shapes the stories — so stories are written after that evidence, not before.
- **Status of existing stories (updated 2026-10-26):** `attempts/` is the first story written from POC evidence (see the log) and is in progress; its POC tasks CMR-ATT-1 to CMR-ATT-3 and CMR-ATT-8
  (report) are done. Phase 2, the formal recreation of code and data, is open: CMR-ATT-4 to CMR-ATT-6, CMR-ATT-9 (linear/VOD and device data) and CMR-ATT-7 (graduation). The other five sub-story
  folders (`metric-definitions-data-inventory/`, `attempts-concurrent-plays/`, `vpf-vsf/`, `ebvs/`, `scratch-validation/`) are placeholder guesses, superseded by the POC-first flow above: each metric
  gets its story only after its POC output is accepted. Do not follow their tasks, and do not delete or rewrite them without an explicit go-ahead. `attempts-concurrent-plays/` is left as is and now
  covers concurrent plays only.
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

## Deliverable pattern for every metric

Each metric ends up with a chart plus a supporting markdown report that helps a reader understand the data. Attempts is the reference (`attempts/`, the POC report for ZA, 2026-10-24). Per metric:

- **Chart(s):** the main time series on the shared theme and `scratch/_lib/line_chart.py` (`render_line`); a second chart where a split explains the number (for attempts, linear vs VOD).
- **Report sections:** definition and method (Conviva wording, counting rule, bucket, timezone); headline numbers (total, peak, sum-of-series check); top-10 content; device breakdown; source
  reconciliation with deltas and reasons; known gaps and assumptions; reproduction (command, query slug, inputs).
- **One data source per report:** use the source the chart uses (Athena for attempts) so the numbers reconcile. Show an "Unresolved" row for sessions missing the field, so tables add up to the total.
- **Data gaps are tasks, not guesses:** when local data lacks a split (attempts: no linear marker, no device type), record it as a data-gap task and find the source with the user. Do not infer it.
- **POC first, story second:** the POC in `scratch/` is not a story deliverable; it only produces the accepted chart and report. The story is written afterwards and describes the formal build: tested
  code (investigation-specific in its scripts, shared functionality in `src/lib/`), catalogued queries and saved exports, generic for any tenant and date, with the user's separate go-ahead.
- **Output location:** reports go to the metric's story folder as `<date>_<tenant>_<metric>-report.md`; charts stay in the gitignored `output/<TENANT>/charts/`, so decide how the image is shared.

## How to turn a POC into a story

The attempts POC exists to formalise how everything is created, not to be shipped. Once a metric's POC and its report are accepted, write its story the same way `attempts/` was written, only with the
user's go-ahead:

1. **Start from the template:** `cp -r docs/plan/_TEMPLATE/story docs/plan/conviva-metrics-recreation/<metric>` (the `prompt.md`, `stories.md` and `tasks.md` set; see `docs/plan/README.md`), and add
   its row to the epic `README.md`.
2. **`prompt.md`:** why the story exists, the Conviva definition with its doc link, the POC result table (sources, counts, deltas), the scope guard, and the task overview.
3. **Tasks are the formal build only:** the POC is referenced as evidence (commit SHAs), not listed as deliverable tasks. Order: explain the gaps, settle the definition points, prove it generalises to
   another tenant and date, close the data gaps (splits the POC could not make), and finally graduate. Shape the tasks with `docs/refactor/` and the design guidelines.
4. **Graduate means all of it:** a tested `scripts/dev/` script and report writer, a `src/lib/charts/` renderer, Athena queries in the catalog (`docs/guides/query-catalog.md`), saved exports for every
   input, registry updates, and the scratch copies retired. Tenant and date are arguments; per-tenant mappings are documented parameters.
5. **Specify each task in `stories.md`:** files, what to implement, tests (happy path and error case, offline) and the commit message. One task per session, one commit per task.
6. **Gate:** graduation needs its own go-ahead after the gap, definition and generalisation tasks are done. Markdown must pass the 200-character reflow hook.

## How to run a session

1. **Recap** — in a few lines, state what the Discussion log says has been decided and what is still open.
2. **Pick one topic** — ask the user which metric or question to work on this session (do not assume). One metric or one question per session keeps the discussion focused.
3. **Understand the definition** (flow step 1) — work from the Conviva documentation the user provides or points to. If a definition is ambiguous or missing, say so and ask; never invent one.
4. **Check local sources** (flow step 2) — look in `investigations/ctap-smvod/data/` and other local data for the ZA tenant on 2026-10-24: can the metric be regenerated from what is already held?
   State which inputs are present and which are missing.
5. **Fetch the missing links** (flow step 3) — only for inputs not available locally, query Lightstep or Athena (after tenant resolution), scoped to ZA and 2026-10-24. Save what is fetched where later
   sessions can reuse it, and say what was added.
6. **Discuss** — for the chosen topic, cover: the definition; the inputs and where each comes from; the likely POC approach; what would make it not reproducible; and how it generalises to other opcos
   and dates. Give a recommendation, not just options. For charts, follow `docs/guides/chart-guidelines.md` and reuse `scratch/_lib/line_chart.py` (`render_line`) before writing a new renderer.
7. **Propose, then wait** (flow steps 4-6) — if a POC script or a story seems warranted, state the plan (files, purpose) and wait for explicit go-ahead; a story is proposed only after the chart and
   report are accepted. All POC scripts live in the top-level `scratch/` folder (not under `docs/plan/`, `scripts/` or `src/`) and follow `scratch/SCRATCH.md` and `docs/guides/query-catalog.md`.
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

### 2026-10-26 (later) — Attempts: supporting report and phase 2

- **Decided:** every metric gets a chart plus a supporting markdown report (see "Deliverable pattern"). The attempts POC script now writes `attempts/<date>_<tenant>_attempts-report.md`: chart,
  headline, and a top-10 content table from Athena `session.csv` only (same source family as the chart). ZA, 2026-10-24: 3,901 attempts; 3,763 match `session.csv`, 3,760 have a title, 141 unresolved.
  Commit `01d0df6`. The attempts story is not closed: the POC only shows how; the story now also covers formally recreating all the code and the data (CMR-ATT-7), preceded by CMR-ATT-9.
- **Data findings:** local ZA data is VOD-only (`abr-vod-` session ids, VOD URLs), so a linear vs VOD chart needs a new source; `session.csv` has no device model/OS, only a hashed `deviceId`.
- **Open:** where linear sessions live (service or session prefix); where device type lives; content is a title not an asset ID; the chart PNG is gitignored, so the report image link only works
  locally.
- **Next topic:** ask the user (CMR-ATT-9 data scouting, CMR-ATT-4 gap probe, or the next metric).

### 2026-10-27 — Prompt reworked into a POC-first flow

- **Decided:** the scratch POC is not a story deliverable (the attempts tasks had to be recreated because it was treated as one). Flow per metric: learn the Conviva definition, check local data, fetch
  from Lightstep or Athena only for gaps, produce a graph and a markdown summary in a scratch script, finalise with the user, then create the story from `docs/refactor/` and the design guidelines. The
  epic ends in a complete `investigations/<slug>/` folder; common code goes in `src/lib/`, investigation-specific code stays in its scripts. Each transition needs an explicit go-ahead. The five
  placeholder sub-stories are marked superseded, not deleted.
