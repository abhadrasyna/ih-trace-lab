# Knowledge: CTAP/SM-VOD Session Correlation — Reusable Findings

> Distilled from the `ctap-smvod-session-report/` submodule (a continuous data-gathering project — MTN SA playback session reporting, started 10 Jul 2026). This file captures only what's **reusable
> beyond that one pipeline** — Athena schemas, join-key semantics, and hard-won gotchas that any future MTN SA / CTAP / SM-VOD / CDN investigation should know before re-deriving them from scratch. For
> full narrative, exact SQL, and script-level detail, follow the links back into the submodule — this doc deliberately does not duplicate that detail. Read this first when: joining CTAP/SM-VOD/Athena
> session data, debugging playback failures/error codes, or correlating CDN logs to sessions. The VOD metadata-side view of the same `sm-vod` traces is distilled separately in
> `knowledge/vod-asset-ingestion-pipeline.md`.

---

## 1. Data source pattern: manual CSV export, not live API

Both Lightstep and Athena are queried by **manually exporting query results to CSV** and dropping them in `inputCSV/` / `queries/`, not via live API/boto3 calls — this was a deliberate choice (see
`ctap-smvod-session-report/README.md` §6 for why). If you're setting up a similar recurring pipeline, default to this pattern rather than assuming live API access will be available/authorized.

## 2. Primary join key: `sessionId`

The bridge key across **every** source in this pipeline is the session ID, format `abr-vod-<uuid>` — present as:
- `sessionId` in CTAP/SM-VOD exports
- `parent_session_id` in Athena `unified_sessions` (rename on join)
- Recoverable indirectly via CDN `content_uuid` correlation (see §4) when no direct session id exists in CDN logs

For the per-service tag names on the same `ctap`/`sm-vod` spans, see `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`; for reusable Lightstep query shapes against those spans, see
`knowledge/mtn-sa-lightstep-query-templates.md`.

## 3. Athena tables for playback outcome (`unified_e6auj7k7` database)

| Table | Use it for | Key fields | Gotchas |
|---|---|---|---|
<!-- lint-ignore-length -->
| `unified_sessions` | Playback outcome (success/fail), first-class columns, no JSON parsing | `parent_session_id` (= `sessionId`), `user_id` (= `householdId`, exact match), `device_id` (= `deviceId`, exact match), `event_type`, `endreason` | **Multi-row per session** — one row per lifecycle `event_type` (`REQUEST_VIEWING`, `PLAY`, `BUFFERING`, ...). The `PLAY` row is the session-summary row. `endreason = 'PLAYER_ERROR'` on the `PLAY` row = failure; `DESTROY` = normal end; `PLAYING` = in-progress. Only gives the error **flag**, not the reason/code. |
<!-- lint-ignore-length -->
| `e6auj7k7_ccl_debug_events` | Error **detail** (code + description) when `unified_sessions` says `PLAYER_ERROR` | `eventtype`, `eventid = 'PLAYER_ERROR'`, `errorcode` (e.g. `1003`), `errordescription` (e.g. `"E81003: Content cannot be played on your current network."`) | Raw JSON-per-row (`json_extract_scalar` needed for most fields). **Rows can be exact duplicates** (at-least-once delivery) — dedupe before use. The `result` field on `PLAYER_SESSION_EVENT` rows is **not** outcome — it only reflects whether the lifecycle create/destroy call itself succeeded (shows `"SUCCESS"` even for failed sessions). |

Full DDL, sample rows, and query history: `ctap-smvod-session-report/queries/QUERY_CATALOG.md` and `queries/exploration/`.

## 4. CDN content-UUID — where it actually lives

If you need to correlate a session to CDN edge logs and don't have a direct join key:

- **The CDN delivery UUID is directly available on the SM-VOD `POST /streamingSession` span**, tag `session.playbackURL` / `playbackURL` — e.g.
  `https://vod-dai-ott-eu2.ssai.iris.synamedia.com/tenant/sun902py/sa-vod.cdn.yellotv.mtn.com/iye9omdf/dash-wv-pr/vode/<uuid>/second_screen.mpd`. The `<uuid>` after `/vode/` or `/vodc/` is the CDN
  content UUID.
- **CTAP's own span does NOT carry this UUID.** CTAP's `POST /ctap/:uxApiVersion/devices/me/playsessions` span only has the catalog-level `request.contentId` — the CDN UUID is generated downstream
  inside SM-VOD's packaging/delivery lookup and only surfaces on SM-VOD's `streamingSession` response span. Don't waste time digging through CTAP or packaging/DRM child spans for it.
- **Regex gotcha:** the delivery path varies by DRM vs. clear: `.../dash-wv-pr/vode/<uuid>/...` (DRM) vs. `.../dash-clear/vodc/<uuid>/...` (clear). A regex anchored to `vode` only will silently miss
  `vodc` rows — match `/vod[a-z]/([a-f0-9-]+)/` instead.
- Before this was found (17 Jul 2026), the fallback was a manifest-timestamp-anchoring heuristic (matching by request timing, not a real key) — only needed for CDN log rows that predate this field
  being added to the export, or if a similar future case doesn't have the span tag available.

## 5. CDN/IP correlation pitfalls (if matching sessions to raw CDN IP logs)

- **Don't greedily match nearest-available block.** On IPs with dense bursts (many sessions + many CDN blocks within seconds of each other), greedy nearest-match lets an earlier session "steal" a
  block that chronologically belongs to a later one. Use an order-preserving (non-crossing) optimal matching per IP instead (sequence-alignment style DP: maximize match count, then minimize time-diff
  among ties).
- **Don't classify by (IP, time-window) alone when multiple concurrent streams share an IP.** A shared IP with two simultaneous content streams will misattribute one stream's CDN errors (e.g.
  `ERR_CLIENT_ABORT`) to the other. Anchor by content UUID (§4) — or manifest-request timing if no UUID is available — to isolate which CDN rows actually belong to which session before classifying a
  root cause.

Full bug write-ups: search `ctap-smvod-session-report/docs/STATUS.md` for "🐛 Fixed dense-burst matching bug" and "🐛 Fixed shared-IP false-positive bug" (both 17 Jul 2026).

## 6. Process conventions worth reusing elsewhere

These aren't CTAP/SM-VOD-specific — they're workflow habits from this submodule worth applying to any similar recurring-data-pipeline project:

- **Plan → inform → act, always** — never edit/run/delete/overwrite anything (code, CSVs, docs) without stating the plan and getting go-ahead first. (This workspace's own equivalent: see "Working
  Agreement" in `.github/copilot-instructions.md`.)
- **Commit after every approved change, same turn** — don't wait to be asked separately once a change is approved and made.
- **All scripts live permanently under `scripts/`** with descriptive names and relative paths — never throwaway/ad-hoc scripts outside the repo.
- **Promote reusable findings to parent `knowledge/`** (this file is the example) when a submodule/investigation accumulates cross-cutting facts — link back to the detailed source, don't duplicate the
  narrative.

---

**Source:** `/Users/abhadra/github_copilot/knowledge/ctap-smvod-pipeline.md`, itself distilled from `ctap-smvod-session-report/docs/STATUS.md`, `queries/QUERY_CATALOG.md`, `LEGEND.md`, and `README.md`
(as of 17 Jul 2026). Harvested into this repo for RKH-2; later edits may add cross-links without re-harvesting the underlying source. These source paths are read-only reference, not a shared codebase.
