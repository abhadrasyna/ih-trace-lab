# Daily 3016 sub-category report (ctap-smvod) — prompt

> Each day, split the SMVOD player errors 3016 (plus 3014/3015) into the 5 Media Playback Errors triage sub-categories, and emit two CSVs per OpCo: a summary and a per-event detail file.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The "Media Playback Errors - Analysis" triage table (Confluence, personal space `~ganesan`, not readable via the Confluence MCP — the table was shared as an image) groups the 3016 family into five
sub-categories, each with an owner, a priority and an "Action for TCS". The investigation already holds the 3016 events locally (`output/<OPCO>/error_eventdata_flat/*_all.csv`), but nothing assigns an
event to a sub-category, so the table's counts cannot be reproduced or tracked per day.

A scratch POC (`scratch/2026-10-24_ctap_smvod_3016_subcategory_sample.py`, sample in `scratch/2026-10-24_3016_sample_out/ZA/`) proved the approach on ZA 2026-10-22: 35 events of 3016 plus 8 of
3014/3015 classified, and `sessionId` joined 35 of 35 to `*_setupsession_with_outcome.csv`. Review of the sample decided the scope: the summary and events CSVs are useful, the "evidence" CSV with an
automatic pattern verdict was not, so it is dropped. The events CSV must also carry the raw user agent so browser/device analysis can be redone without re-joining.

## Scope guard

- **In bounds:** `investigations/ctap-smvod/scripts/`, `investigations/ctap-smvod/tests/`, `investigations/ctap-smvod/docs/`, `investigations/ctap-smvod/output/<OPCO>/subcategory_3016/`, plus the root
  `SCRIPTS.md` and `CONTEXT.md` entries.
- **Out of bounds:** `src/`, other investigations, any Athena or Lightstep query (the report reads existing local CSVs only), the evidence/pattern-verdict CSV, segment-corruption checks, and mDRM/CDM
  lookups.
- Tooling only; no runtime behaviour of any service changes.

## Session-start load hints

- `scratch/2026-10-24_ctap_smvod_3016_subcategory_sample.py` — the POC to graduate; reuse its classification rules and join logic.
- `investigations/ctap-smvod/scripts/flatten_error_eventdata.py` — produces the `error_eventdata_flat/*_all.csv` inputs (columns `errorcode`, `pipeline_status`, `media_error_type`, `user_agent`,
  `sessionId`, `householdId`).
- `docs/guides/functional-code-taxonomy.md` — read before adding any shared helper; keep this story's code inside the investigation.

## Task overview

- **SUB-1** — rules module: map one flat error row to a sub-category and priority.
- **SUB-2** — events builder: join to setupsession/position by `sessionId`, add parsed fields and the raw `user_agent`.
- **SUB-3** — summary builder: events and distinct households per OpCo and sub-category.
- **SUB-4** — daily CLI: run both builders for an OpCo and date range, write the CSVs, reconcile counts.
- **SUB-5** — docs and registry: usage doc, `SCRIPTS.md`, `CONTEXT.md`, retire the scratch POC.

## Definition of done

Running the CLI for any OpCo/day writes `<date>_subcategory_summary.csv` and `<date>_subcategory_events.csv`; the event total equals the day's 3014/3015/3016 rows in the flat file; tests are green and
offline; the usage doc and registries are updated.

## Perspectives not covered

- Segment URLs exist locally only on 3014/3015 events; 3016 events have none, so "map by segments" for video decode errors needs CDN logs (a separate story).
- Chrome's reduced user agent hides the Android model (mostly "K"); the real device needs mDRM/CDM logs (a separate story, `docs/plan/ctap-smvod-3016-drm-device-link`).
- Whether a content or household "pattern" exists is left to the analyst reading the events CSV; no automatic verdict is produced.
