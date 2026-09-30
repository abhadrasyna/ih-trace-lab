# Knowledge: VOD Asset Field Mapping (OpsHub ↔ ADI ↔ CTAP ↔ MongoDB)

## Read this first when

Consult this before tracing a VOD asset's metadata across OpsHub, ADI XML, HAR, Lightstep, and MongoDB for MTN SA, or when you need to navigate OpsHub using an ID seen in a trace, HAR, or MPD.

## Four ID families you must keep separate

The VOD ingestion flow uses four different ID families. They are related, but they are not interchangeable.

| ID family | Example | Where you see it | How to use it | Never interchange with |
| --- | --- | --- | --- | --- |
<!-- lint-ignore-length -->
| Physical Content ID (`IngestUID`) | `c78f1cbb-c34a-5269-93ea-fb215e7ef8d1` | MPD/CDN/license URLs, `sm-vod` `otherId`, OpsHub Assets `physicalContentId` | Search OpsHub Assets with this value to find the playback asset. | Internal Content ID, Package Asset ID, Show/Season ID |
<!-- lint-ignore-length -->
| Internal Content ID (`baseContentId`) | `ddb4bc9b-ded6-5738-b5ae-699880e6353f` | `contentInstances.baseContentId`, first `id` segment, OpsHub Status "Internal Content ID" | Use this for catalogue/detail lookups and services keyed to the catalogue object. | Physical Content ID, Package Asset ID, Show/Season ID |
<!-- lint-ignore-length -->
| Package Asset ID | `AKNG0000000000700000` | OpsHub Status tab, ADI filename, `contentInstances.externalPackageId` | Use this on the OpsHub Status tab to check ingest and packaging state. | Physical Content ID, Internal Content ID, Show/Season ID |
<!-- lint-ignore-length -->
| Show ID / Season ID (series only) | `TIME_47_0001400000` / `TIME_47_0001401000` | `contentInstances.showId` / `seasonId`, `shared/content`, OpsHub Status Show/Season ID columns | Use these for series hierarchy browsing and OpsHub status matching. | Physical Content ID, Internal Content ID, Package Asset ID |

The client-facing `contentInstances.id` is itself a compound value:

```text
{Internal Content ID}~{Provider_ID}_{Provider_TitleAssetID}~vod
```

Example:

```text
ddb4bc9b-ded6-5738-b5ae-699880e6353f~AKNG_AKNG2100000000700000~vod
```

That compound form is useful for recovering the provider/title segment, but it is still anchored on the Internal Content ID, not the Physical Content ID.

## Lightstep correlation gotcha

For series traces, `session-guard` and downstream `ctap`/`vodcontent-get` spans can share the same `FCID` while carrying different `otlp.trace_id` values. Treat `FCID` as the cross-hop key there;
trace ID alone does not bridge that edge-to-backend hop.

## ADI → `contentInstances` → MongoDB field chain

This table condenses the reusable field correspondences from the API and Mongo write-ups into one lookup reference.

| ADI field | `contentInstances` field | Mongo field/path | Notes |
| --- | --- | --- | --- |
| `AMS.Asset_ID` (package asset) | `externalPackageId` | `common.externalPackageId` | Package Asset ID; exact match across ADI, API, and Mongo. |
| `AMS.Asset_ID` (title asset) | `externalId` | `common.externalId` | Title asset ID, distinct from the package asset ID above. |
| `Title` | `title` | `eng.title` | Exact content title match. |
| `Summary_Short` / `Summary_Medium` | `synopsis` | `eng.synopsis`, `eng.shortSynopsis` | API exposes only the curated synopsis field, not both source variants. |
| `Summary_Long` | `longSynopsis` | `eng.longSynopsis` | Exact long synopsis mapping. |
| `Rating` | `parentalRating.name` | `common.parentalRating` | The API surfaces the rating name and a derived numeric value, but not the source regional metadata. |
| `X_Regional_Rating` | — | — | Dropped before the API surface; scheme/region are not exposed. |
| `Advisories` | `contentAdvisories[]` | `common.advisories[]` | API emits advisory flag/display values from stored advisory data. |
| `Year` | `productionYear` | `common.productionYear` | Exact match. |
| `Country_of_Origin` | `productionLocation` | `common.productionLocation` | Exact match. |
<!-- lint-ignore-length -->
| `Actors` | `credits.actors[]` | `eng.credits[].personGivenName` + `personFamilyName` | Mongo already stores names pre-split; the API joins from structured names, not from raw `Last, First` ADI text. |
| `Director` | `credits.directors[]` | `eng.cast.directors` | Same pre-split / structured-name pattern as actors. |
| `Producers` | — | — | Dropped entirely from the API. |
| `Genre` | `genres[]` | `common.genres[]` | Exact list mapping. |
| `Category` | — | — | Dropped before Mongo/API lookup surfaces. |
| `X_Keyword` | — | `common._keywords[]`, `eng.keywords[]` | Stored in Mongo but not exposed through `contentInstances`. |
<!-- lint-ignore-length -->
| `Run_Time` | `duration` | `common.duration` | Precision increases downstream: ADI uses whole seconds, Mongo stores milliseconds, and MPD shows sub-second packaged duration. Sub-1s ADI↔MPD deltas are expected. |
| `Licensing_Window_Start/End` | entitlement-gated, not shown directly | `common.licenseStart`, availability fields | Drives entitlement logic rather than a first-class API field. |
| `Audio_Type` | `audioFormat` | `common.audioType` | Exact semantic mapping. |
| `Languages` | `audioLanguages[]` | `common.audioLanguages[]` | Exact list mapping. |
| `X_Movie_Format`, `HDContent` | `videoFormat` | `common.videoFormat` | Curated to the client-facing format field. |
| `X_Break_Position` | — | — | Not exposed in the API, but it still matches MPD Period boundaries and SCTE-35 splice timing. |
| supporting-image assets (`CLEAR_POSTER_*`, `POSTER_*`, logo) | `media[]` | `eng.thumbnails[]` | Image metadata survives into Mongo and the API, but file size/checksum details do not. |
| offer-window data | `contentFlags: ["subscription"]` | `common.flatOfferTimeWindowMap` | Reduced to entitlement/flag semantics; offer/catalogue detail is not passed through. |
| — | `id` | `_id` plus synthetic `~vod` suffix | Mongo stores the compound ID without the trailing `~vod`; that suffix is added later in the API path. |
| — | `baseContentId` | `vmsId`, `common.assetId` | Internal Content ID. |
<!-- lint-ignore-length -->
| — | `showId`, `seasonId`, `episodeNumber`, `seasonNumber` (series only) | top-level + `common.showId` / `common.seasonId` and episode/season number fields | These originate at Mongo storage for series content; they are not API-only synthesis. |
| — | `lastPlayPosition`, `bookmarks[]` | — | Session/editorial state, not ADI-authored content metadata. |

## About the auto-generated `common-field-mapping*.md` matrix

`vod-asset-ingestion-mapping/data/opshubs/common-field-mapping-overview.md` and `common-field-mapping-details.md` are the freshest per-Asset-Class coverage matrices across six layers: OpsHub Assets,
OpsHub Status, `contentInstances`, Lightstep `ctap`, Lightstep `sm-vod`, and MongoDB. They are generated by `scripts/build_common_field_mapping.py` using value matching, not field-name matching, so
they are excellent for spotting likely correspondences and coverage gaps.

One caveat matters enough to repeat here: some small-integer matches are confirmed noise, not real field correspondences. The series work explicitly calls out examples like `"1"` matching
`AMS.Version_Major` against unrelated counters. Treat every ✓ in those matrices as a lead to validate, not automatic proof of a semantic mapping.

## Source

Source paths: `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/opshub-asset-id-mapping.md`, `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/ctap-query-mapping.md`,
`/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/docs/mongodb-mapping.md`, `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/data/opshubs/common-field-mapping-overview.md`, and
`/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/data/opshubs/common-field-mapping-details.md`. These files are read-only reference, not a shared codebase.
