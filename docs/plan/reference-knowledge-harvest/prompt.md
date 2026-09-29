# Reference knowledge harvest — prompt

> The ongoing, docs-only vehicle for pulling reusable knowledge out of `github_copilot`'s ~13 read-only investigation folders into `ih-trace-lab/knowledge/`, one folder at a time. This is not a
> one-off — new tasks (`RKH-3`, `RKH-4`, ...) get appended here each time a new source folder is next up for harvesting. The first batch (`RKH-1`/`RKH-2`) covers `vod-asset-ingestion-mapping/`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Reusable facts (field mappings, gotchas, query templates, span-attribute references) accumulate across `github_copilot`'s investigation folders but stay siloed there — each is read-only reference, not
wired into `ih-trace-lab` as a submodule, so nothing crosses over automatically (see `CONTEXT.md`'s constraint: that tree is prior art, not a shared codebase). This story is the repeatable process for
closing that gap: pick one source folder, compare it against the root `github_copilot/knowledge/` files that already reference it, and land a distilled, corrected, cross-linked knowledge file here —
then move to the next folder as its own task, never bundling multiple folders into one task.

The first folder up is `vod-asset-ingestion-mapping/` (a recurring MTN SA investigation submodule): it has already built an auto-generated, value-matched field-mapping matrix tracing a VOD asset
across ADI XML → OpsHub → HAR → Lightstep spans → MongoDB → CTAP response, plus an ID-navigation cheat sheet (Physical/Internal Content ID, Package Asset ID, Show/Season ID). The root
`github_copilot/knowledge/` folder already distilled a first pass of this (`vod-asset-ingestion-pipeline.md`) plus an adjacent CTAP/SM-VOD session-correlation pipeline (`ctap-smvod-pipeline.md`,
sharing the same `ctap`/`sm-vod` spans) — both worth pulling into `ih-trace-lab` alongside a fresher pass over the submodule's own docs, since the root distillation is already stale in at least one
place (it says the MongoDB layer "hasn't started"; the submodule's own `STATUS.md` shows that layer closed out as of its "stage 6" entry).

## Scope guard

**Per-task rule (applies to every RKH task, present and future):** exactly one `github_copilot/*` source folder plus the root `github_copilot/knowledge/` files that reference it — never two
investigation folders compared/bundled in the same task. Sources are always read-only, never edited.

**This batch (RKH-1/RKH-2) — folder under harvest: `vod-asset-ingestion-mapping/`:**
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/` — specifically `docs/opshub-asset-id-mapping.md`, `docs/ctap-query-mapping.md`, `docs/mongodb-mapping.md`, `docs/STATUS.md` (for the
  stage-6 MongoDB correction), and `data/opshubs/common-field-mapping{,-overview,-details}.md`.
- `/Users/abhadra/github_copilot/knowledge/vod-asset-ingestion-pipeline.md` and `/Users/abhadra/github_copilot/knowledge/ctap-smvod-pipeline.md`.

**Not in this batch, but not out of scope for this story either — future tasks, not yet numbered:** every other `github_copilot/*` project folder (`applauseInvestigation`, `ctap-smvod-session-report`,
`astro-events-household-report`, etc.) gets its own future `RKH-N` task in this same story, scoped the same narrow way (root `knowledge/` + that one folder) once it's next up. In particular,
`applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` (a per-service Lightstep tag/attribute reference — genuinely useful for MCP querying, and it already documents
`ctap`/`sm-vod`/`session-guard`, all seen in this submodule's own traces) is **not** harvested by RKH-1/RKH-2 — RKH-2 leaves an explicit pointer to it so a future `applauseInvestigation` task (added
here, not a new story) picks it up (and can extend it with the 4 services — `vodcontent-get`, `favm`, `viewinghistory-viewing-history`, `tstv-capture-bc` — that only appear in this submodule's trace
JSONs, not in that file today). No script/`scripts/lib/` porting in this story — matrix regeneration against new assets is a separate, larger decision if ever needed. No live MCP/Athena/Lightstep
call.

## Session-start load hints

- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/opshub-asset-id-mapping.md` — the ID-navigation cheat sheet (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/ctap-query-mapping.md` — ADI → CTAP response field table, incl. §5 series-specific fields (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/mongodb-mapping.md` — ADI/API → MongoDB layer (read-only source, do not edit).
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/STATUS.md` — read the "series, stage 6 — MongoDB layer" entry specifically, it's the correction source for RKH-2.
- `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/data/opshubs/common-field-mapping-overview.md` (+ `-details.md`) — the auto-generated per-asset-class matrix (read-only source, do not
  edit).
- `/Users/abhadra/github_copilot/knowledge/vod-asset-ingestion-pipeline.md`, `/Users/abhadra/github_copilot/knowledge/ctap-smvod-pipeline.md` — the two root-level distillations being harvested
  (read-only source, do not edit).

## Task overview

**This batch (`vod-asset-ingestion-mapping/`):**
- **RKH-1** — `knowledge/vod-asset-field-mapping.md`: harvest the submodule's own docs (ID-navigation table + ADI→API→Mongo field tables + the auto-generated common-field-mapping matrix summary) into
  one distilled, ih-trace-lab-native knowledge file.
- **RKH-2** — `knowledge/vod-asset-ingestion-pipeline.md` + `knowledge/ctap-smvod-pipeline.md`: port both root `github_copilot/knowledge/` distillations, correct the stale MongoDB-gap claim,
  cross-link to RKH-1's output, and add the explicit "not yet harvested" pointer to `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`.

## Definition of done

- `knowledge/vod-asset-field-mapping.md` states the four-ID-family navigation table and the ADI→API/Mongo field correspondences clearly enough to answer "which OpsHub/HAR/Lightstep/Mongo field does
  ADI field X map to" without opening the submodule.
- `knowledge/vod-asset-ingestion-pipeline.md` and `knowledge/ctap-smvod-pipeline.md` exist in `ih-trace-lab`, matching the source distillations but with the MongoDB-gap claim corrected and a
  cross-link to `knowledge/vod-asset-field-mapping.md` (no duplicated field tables between the three files — link, don't repeat).
- `knowledge/vod-asset-ingestion-pipeline.md` carries one clearly-flagged "Related, not yet harvested" pointer to `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`.

## Perspectives not covered

- RKH-1/RKH-2 do not attempt to harvest or even summarize any other `github_copilot/*` project — each future folder gets its own `RKH-N` task, added to this same story when that folder is next up,
  never bundled with another folder's task.
