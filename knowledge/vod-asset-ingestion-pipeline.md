# Knowledge: VOD Asset Ingestion Pipeline (OpsHub → MongoDB → CTAP)

> Detailed narrative and raw artifacts live in the `vod-asset-ingestion-mapping/` submodule. This file only distills reusable facts and links back — don't duplicate the full walkthroughs here.
> Supersedes (merged 2026-08-30): `knowledge/opshub-asset-id-mapping.md`, `knowledge/adi-contentinstances-mpd-mapping.md`.

## Read this first when

You need to trace how a VOD asset's metadata flows: **OpsHub ingestion (ADI XML) → MongoDB storage → CTAP query response → client display**, for MTN SA (or need to navigate OpsHub using an ID seen in
a trace/HAR/ MPD, or vice versa).

## Distilled facts

- **Content ID vs Package Asset ID are different IDs, both needed to navigate OpsHub.** Content ID (e.g. `c78f1cbb-c34a-5269-93ea-fb215e7ef8d1`) is what appears in MPDs/HAR/Lightstep traces and is
  used to search OpsHub's Assets screen. Package Asset ID (e.g. `AKNG0000000000700000`) only appears once you've opened the matched asset in OpsHub, and is used on OpsHub's Status tab to check
  ingest/packaging pipeline state. Full detail: `knowledge/vod-asset-field-mapping.md`.
- **ADI is the source; the client-facing `contentInstances` API exposes only a curated subset** — most ADI fields (`Producers`, `Category`, `X_Keyword`, offer/catalogue detail, `X_Regional_Rating`
  scheme/region) are dropped entirely. Full field-by-field table: `knowledge/vod-asset-field-mapping.md`.
- **Duration/timing fields reconcile across ADI → API → MPD but with increasing precision downstream** (whole-second editorial metadata → exact packaged-segment timeline) — a sub-1s delta is expected,
  not a bug. See the duration row in `knowledge/vod-asset-field-mapping.md`.
- **`X_Break_Position` (ADI ad-break markers) match MPD Period boundaries** but are not surfaced via `contentInstances` at all — only visible by reading the ADI or MPD directly.
- **Player/resume position is not ADI content** — it lives entirely in the session/entitlement layer (`lastPlayPosition`, `bookmarks[]`, `playsessions.startPlayPosition`), never in the static ADI
  package.

## Status

The MongoDB layer mapping is now done for both tracked assets. See `knowledge/vod-asset-field-mapping.md` for the consolidated field chain, and `vod-asset-ingestion-mapping/docs/STATUS.md`'s
2026-08-31 stage-6 entry for the series close-out. The remaining open item across both TAAMA and `TIME_47_0001400000` is the DRM/mDRM Lightstep layer, which still has not been captured for either
asset.

## Related, not yet harvested

`applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` is a reusable per-service Lightstep tag/attribute reference covering `ctap`, `sm-vod`, and `session-guard` among nine
services. It is intentionally deferred to the future `applauseInvestigation` harvest tasks; that future pass should also extend it with the four services only seen in this submodule's trace JSONs:
`vodcontent-get`, `favm`, `viewinghistory-viewing-history`, and `tstv-capture-bc`.

## Where things live

- Full docs, ADI XML, and HAR captures: `vod-asset-ingestion-mapping/` (see its `README.md` and `docs/STATUS.md` for the running log)
- The SM-VOD span and session/CDN correlation details shared with playback investigations are distilled in `knowledge/ctap-smvod-pipeline.md`.
- Original source case (narrative, still historical reference): `investigations/docs/20260722-mtn-sa-taama-license-flow.md`

**Source:** `/Users/abhadra/github_copilot/knowledge/vod-asset-ingestion-pipeline.md`, corrected against `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/STATUS.md` and harvested into
this repo's `knowledge/` story output. Both source paths are read-only reference, not a shared codebase.
