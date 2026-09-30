# vod-asset-ingestion-mapping migration — prompt

> Port `vod-asset-ingestion-mapping` (VOD asset ADI↔OpsHub↔HAR↔Lightstep↔MongoDB field mapping, a recurring campaign) into `investigations/vod-asset-ingestion/` — Tier 2.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`/Users/abhadra/github_copilot/vod-asset-ingestion-mapping` (15 files) has no migration plan anywhere — cited elsewhere only as `har`'s duplication source (`har_parser.py`). Epic `spec.md` §4 audited
it: 4 files are `har`/`csv_io` lib candidates; 11 stay project-specific (ADI XML parsing, ID/value correlation, OpsHub↔HAR field mapping). Note also `docs/plan/reference-knowledge-harvest/` already
harvested this project's VOD asset ID-navigation cheat sheet into `knowledge/` — that is a separate, already-landed docs effort; this story ports the project's *code*, not its knowledge.

**Category correction (epic GAP-1, 2026-09-30):** this project was previously worked-example'd under `experiments/` in `project-taxonomy/structure.md`/`stories.md`. Both files were corrected — its own
README calls it "a continuous data-gathering exercise," a recurring-campaign investigation, not a throwaway experiment. Target is `investigations/vod-asset-ingestion/`, not `experiments/`.

## Scope guard

**In bounds:** `investigations/vod-asset-ingestion/` — auditing/confirming `spec.md` §4's classification, then (later) skeleton + port.

**Out of bounds:** anything under `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping` (read-only, never edited); `src/lib/{har,csv_io}` internals; `reference-knowledge-harvest`'s
already-landed `knowledge/` distillation (not re-touched here); any other sub-story.

## Session-start load hints

- `docs/plan/reference-code-gap-migration/spec.md` §4 — this project's full per-file audit table.
- `docs/plan/reference-code-gap-migration/README.md` §"GAP-1 decisions" — the category-conflict resolution and ADI/XML-mapper accept-local decision.
- `docs/plan/project-taxonomy/structure.md` — the corrected `investigations/vod-asset-ingestion/` example.
- `docs/plan/src-lib-migration/README.md` — `har`/`csv_io` module status.

## Task overview

- **VAI-1** — Audit `vod-asset-ingestion-mapping/` and produce a per-file lib-vs-script classification table, confirming/refining `spec.md` §4.
- Further tasks (skeleton port, tests, `CONTEXT.md` pointer) deliberately not yet written.

## Definition of done

`investigations/vod-asset-ingestion/` exists, fully tested, importing `src/lib/{har,csv_io}` for HAR/CSV concerns; ADI XML parsing, ID-component parsing, and value-index/field-mapping logic stay
local. No file under `/Users/abhadra/github_copilot` was touched.
