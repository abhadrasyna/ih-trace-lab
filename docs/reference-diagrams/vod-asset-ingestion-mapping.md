# Reference diagram — vod-asset-ingestion-mapping

Hand-authored from `knowledge/vod-asset-ingestion-pipeline.md`, `knowledge/vod-asset-field-mapping.md`, and the reference project's own mapping docs. This folder's value is the field/ID chain across
systems, not its internal Python imports.

## Field and ID mapping

```mermaid
flowchart LR
    ADI["ADI XML / OpsHub ingest<br/>authoritative asset metadata"]
    OPS_ASSETS["OpsHub Assets<br/>search by Physical Content ID<br/>(IngestUID)"]
    OPS_STATUS["OpsHub Status<br/>track Package Asset ID,<br/>Internal Content ID,<br/>Show/Season IDs"]
    MONGO["MongoDB content store<br/>common.* / eng.* fields"]
    CTAP["CTAP contentInstances / shared-content APIs<br/>curated client-visible subset"]
    HAR["HAR / client API traffic<br/>request + response bodies"]
    LIGHTSTEP["Lightstep traces<br/>ctap / sm-vod / session-guard spans"]
    MPD["MPD / playback URLs<br/>packaging + delivery layer"]

    ADI -->|AMS.Asset_ID package| OPS_STATUS
    ADI -->|field payload via OpsHub ingest| MONGO
    ADI -->|title, synopsis, rating, advisories,<br/>runtime, languages, media| MONGO
    ADI -->|X_Break_Position matches Period boundaries| MPD

    OPS_ASSETS -->|physicalContentId = IngestUID| MONGO
    OPS_STATUS -->|Package Asset ID / Internal Content ID / Show/Season IDs| MONGO

    MONGO -->|common.externalPackageId = Package Asset ID| CTAP
    MONGO -->|vmsId / common.assetId = Internal Content ID<br/>-> baseContentId| CTAP
    MONGO -->|eng/common metadata subset| CTAP
    MONGO -->|series hierarchy: showId / seasonId / episodeNumber| CTAP

    CTAP -->|JSON responses: id, baseContentId,<br/>externalPackageId, showId, seasonId| HAR
    CTAP -->|request.contentId / shared-content params| LIGHTSTEP

    HAR -->|compound id = {Internal Content ID}~{Provider}_{TitleAssetID}~vod| LIGHTSTEP
    LIGHTSTEP -->|sm-vod otherId includes IngestUID label| OPS_ASSETS
    LIGHTSTEP -->|otherId / contentId / request.contentId confirm ID families| OPS_STATUS
    LIGHTSTEP -->|playbackURL / contentId / otherId carry Physical Content ID| MPD

    MPD -->|Physical Content ID appears in playback / license flow| OPS_ASSETS
```

## Reading the diagram

- Keep the four ID families separate: **Physical Content ID (`IngestUID`)**, **Internal Content ID (`baseContentId`)**, **Package Asset ID**, and, for series only, **Show/Season IDs**.
- `contentInstances.id` is a synthetic compound value anchored on the **Internal Content ID**, not the Physical Content ID.
- ADI is the source of truth, but CTAP exposes only a curated subset; fields like `Producers`, `Category`, `X_Keyword`, and regional-rating metadata are dropped before or at the API layer.
- `X_Break_Position` never surfaces in CTAP, HAR, or Lightstep responses, but it still lines up with MPD Period boundaries, so the playback layer remains part of the same evidence chain.

## Convergence target

Per GAP-1, this folder is **not** an `experiments/` candidate. Its target category is `investigations/vod-asset-ingestion/`: a recurring investigation whose reusable outputs are the mapping facts
above, while the ADI/XML identity logic stays local rather than promoting a new `src/lib/*` module.
