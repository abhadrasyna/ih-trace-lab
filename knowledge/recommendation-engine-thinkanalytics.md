# Recommendation engine ("More Like This" / related content) — architecture & vendor facts

Distilled reusable facts from investigating MTN SA ticket PRB0069833 (2026-08-05). Full narrative/evidence: `../investigations/docs/20260805-mtn-sa-onetv1-morelikethis-recommendation-relevance.md`.

**Related:** `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` covers the tenant-specific MTN SA versus TIM Play flow differences that overlap with this note; keep that file for the
case-level comparison and this one for the distilled reusable rule set.


## Architecture (GO/IH platform)

- **"More Like This" / related-content recommendations** are served through this chain: `client` → CTAP `GET /ctap/v1/agg/recommendations/related?contentId=...&source=vod&limit=N` → `IH/ctap` plugin
  `cma/plugins/he_api/IH/1.0.0/vsoapi/recommendations_he_api.js` → `recommendrelated` service (repo `IH/recommend`, Lightstep service `recommendrelated` in `mcs-go-prod-iye9omdf-eu`) → Redis cache
  (`utellyRedis.js`), keyed `source~contentId` → underlying similarity/ranking model = **external, vendor-hosted**.
- `recommendrelated` is a **caching/proxy layer only** — it does not compute similarity. If no cache entry exists for a contentId, it falls back to a global `default_profile` key
  (`config/default.json: defaultProfileKey`) — a generic, non-personalized list. Always check whether a "More Like This" complaint is actually this fallback (empty/206 → default) vs a
  real-but-poorly-ranked response (200, non-empty, real per-title data) — these have very different root causes and were initially conflated in this investigation before the HAR ground-truth ruled out
  the fallback theory.
- CTAP's `recommendations_he_api.js` applies **genre/topLevelFilterTag filtering** for `"context"` and `"preference"` recommendation types (`query.genre()`, `query.excludeGenres()`), but **NOT for
  `"related"`** (recType=RELATED, the "More Like This" case) — that path only sets recType/panelId/cert-check/opted-out/timeWindow/source(asset-type) filter. Whatever the upstream model returns is
  passed through with no relevance re-ranking or genre floor. This is a structural gap worth knowing before assuming a "bug" — it's by design (or an old design gap), not a regression.

## Vendor: "TA" = ThinkAnalytics

- **"TA"** appearing throughout CTAP code (`RecommendationType.RELATED`, `recommendMethod2Panel`, panel IDs 100–112) and in Jira (`CR271 TA recommendation`, `TA Recommendations Data Tuning...`) refers
  to **ThinkAnalytics**, the third-party vendor whose model actually computes recommendation similarity/ranking. It is NOT in Synamedia's own repos — the real weighting/relevance logic is
  opaque/proprietary vendor logic.
- ThinkAnalytics runs as an externally-hosted "aaS" service (migrated out of the CP AWS account per **PMPRJ-7552**, done 2022).
- **Known failure pattern:** relevance quality **degrades over time as the content catalog grows**, requiring a periodic vendor data-tuning re-engagement. Documented precedent: **PMPRJ-13745** ("TA
  Recommendations Data Tuning Activity Support and Keywords Based Recommendations", done for **Astro** platform, 2022–2023) — explicit description: *"recommendation quality... deteriorates over time
  because of the significant growth on library scale since the last tuning done during platform launch."* No equivalent tuning ticket has been raised for MTN SA as of 2026-08-05 — if a similar
  complaint recurs for MTN, check for/raise an analogous ticket referencing PMPRJ-13745 as the template.
- A separate, still-open CR — **PMPRJ-22908** "CR271 TA recommendation" (Epic, Proposal, owner `yblankrot`) — may or may not cover relevance/weighting; worth checking before assuming a new ticket is
  needed.

## "Utelly" — separate, do not conflate with ThinkAnalytics

- `utellyRedis.js` in `recommendrelated` refers to a **different** third-party ("Utelly") used for a related-but-distinct metadata/aggregation cache flow, evidenced by a Confluence page titled `Utelly
  Migration` (content not yet retrieved — see tooling gap below). Don't assume "Utelly" and "ThinkAnalytics" are the same vendor/system just because both are read via the same Redis cache module.

## Tooling gaps hit during this investigation

- Lightstep `get_stored_trace` returned HTTP 500 consistently (not the usual 404/indexing-lag) during this session — a transient MCP/API issue, not a data-availability problem. If this recurs, don't
  waste retries per span; fall back to `query_spans`/`query_timeseries` aggregate error/volume checks instead, which still worked.
- Confluence search (`confluence01_search`) returns `null` for every result's `id`/`space_key`, even via raw CQL — `get_page` then can't resolve `space_key + title` for pages found this way. Tried all
  53 spaces visible via `list_spaces` with no match for `FT166 Analysis...`/`Utelly Migration` — these pages likely sit in a space this connector doesn't index/access. If a future investigation needs
  Confluence content found via search, expect this to fail and ask the user for a direct page URL/ID instead of guessing spaces.
