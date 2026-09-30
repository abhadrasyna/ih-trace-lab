# Reference code gap migration — router

Route to this epic's stories once you know which project/task you're picking up. This file has no tasks of its own — see each story's own `prompt.md` for its routing rules and session-start protocol
(read `CONTEXT.md`, find the first unchecked task in that story's own `tasks.md`, one task per session).

`GAP-1` — the task that produced this epic (scope shape, category-conflict resolution, new-module promotion decisions) — is done; its record lives in this folder's own `tasks.md`/`stories.md` (now
closed) and `spec.md` (the audit evidence still worth reading before any sub-story's first task). See `README.md` for the full decision log, tiering rationale, and story table.

## Why this epic exists

A 2026-09-30 session asked whether `docs/plan/pipeline-migration/` and `docs/plan/src-lib-migration/` together plan for *all* Python code migration out of `/Users/abhadra/github_copilot` (read-only
reference). They do not: ten projects (`vod-playback-timing-probe`, `mtn-zm-session-device-investigation`, `mtn-network-traffic`, `vod-asset-ingestion-mapping`, root `investigations/`,
`applauseInvestigation`, `shaka-6001-sa-error-analysis`, root `scripts/`, `astro-events-household-report`, `smarttv-mtntv`) had zero migration plan. `README.md` records the full decision log for how
this epic now covers all ten.

## Hard gate — read before starting any story

Every story in this epic is blocked until these land:

1. `docs/plan/src-lib-migration/` — the `src/lib/*` modules each story imports must exist and be tested first. Tier 3 stories additionally need the two modules `README.md` §"GAP-1 decisions" promoted
   (`mpd`, `crypto_signing`) — those do not exist yet even after the other five modules land.
2. `docs/plan/project-taxonomy/` — PT-1/PT-2/PT-7 at minimum, for the category definitions and folder skeletons every story's target path assumes.

If these are not yet ✅ done, stop and pick up that story instead — do not re-derive `src/lib/*` module shapes or folder skeletons locally; this epic only consumes them.

## Story selection

| If you're working on… | Tier | Go to |
|---|---|---|
| `applauseInvestigation` | 1 | `applause-investigation-migration/prompt.md` |
| `astro-events-household-report` | 1 | `astro-events-household-investigation-migration/prompt.md` |
| `shaka-6001-sa-error-analysis` | 1 | `shaka-6001-sa-investigation-migration/prompt.md` |
| root `scripts/` | 1 | `root-scripts-tool-migration/prompt.md` |
| `vod-asset-ingestion-mapping` | 2 | `vod-asset-ingestion-investigation-migration/prompt.md` |
| `mtn-zm-session-device-investigation` | 2 | `mtn-zm-device-investigation-migration/prompt.md` |
| `mtn-network-traffic` | 2 | `mtn-network-traffic-tool-migration/prompt.md` |
| root `investigations/` | 2 | `root-investigations-migration/prompt.md` |
| `vod-playback-timing-probe` | 3 (blocked on `src/lib/mpd/`) | `vod-playback-timing-probe-tool-migration/prompt.md` |
| `smarttv-mtntv` | 3 (blocked on `src/lib/crypto_signing/`) | `smarttv-mtntv-tool-migration/prompt.md` |

No priority order is enforced across stories beyond the tiering above — pick whichever one you're asked to work on; land Tier 1 before Tier 2/3 only when no specific story was requested.

## Invariant

Never create, edit, or delete any file under `/Users/abhadra/github_copilot` — it is read-only reference for every story in this epic.
