# Knowledge: MTN SA Lightstep Span Attributes by Service

## Read this first when

Consult this before writing a Lightstep `query_spans`/`query_timeseries` filter or `group_by` against `mcs-go-prod-iye9omdf-eu`, so you use the tag names and casing each service actually exposes.

General method used to build this: pick one representative span per service (from a `query_spans`/raw CSV export), pull full detail via `get_stored_trace`, and record every tag key seen. See
`investigations/instructions/lightstep-mcp-tool-notes.md` for the query syntax rules this relies on.

---

## Universal fields (present on every service sampled)

- `deviceId` — hashed device identifier (also appears as `sessionInfo.deviceId`, `request.deviceId`, `session.deviceId` depending on service)
- `householdId` — (also `sessionInfo.householdId`, `request.householdId`, `session.householdId`)
- `http.status_code`, `http.method`, `http.route`/`http.target`, `http.url`
- `busUnitId` / `sessionInfo.busUnitId` — MTN SA = `iye9omdf`
- `userProfileId` (also `request.userProfileId`, `session.userProfileId`)
- `otlp.trace_id` — the real OTel trace ID (not the same as `get_stored_trace`'s echoed `trace.id` when queried by span_id)
- `span.kind` (`server`/`client`/`internal`)

## Near-universal but inconsistent shape

- **`FCID`** — correlation ID present almost everywhere, but the shape varies:
  - Direct tag `FCID` or `request.FCID` on `ctap`, `channellineup`, `sm-linear`, `sm-tstv` spans
  - Only embedded inside a `logs[].fields.event` string (e.g. `"FCID=6A7C20D81E15CB2900000088,event=SessionCreated,..."`) on `sm-vod` and `households-*` spans — **not directly
    filterable/group-by-able** on those services without parsing the log field
- **`deviceType`** — present on most services (`PC`, seen on `households-api`, `households-core`, `households-transformer`, `sm-vod`, `sm-linear`, `sm-tstv`, `ctap`'s `sessionInfo.deviceType`).
  **Confirmed unreliable as a platform signal** — showed `PC` even for a device confirmed Android via HAR and via its own `http.user_agent` tag. Don't use for mobile-vs-desktop segmentation; use
  `http.user_agent` instead where present.
- **`http.user_agent`** — only present on some spans (seen on `ctap` DELETE playsessions spans, `sm-vod` streamingSession spans) — when present, is the trustworthy platform signal.

## Service-specific fields

### `session-guard` (edge reverse-proxy/gateway in front of CTAP — discovered during issue 7231763 latency investigation, 14 Aug 2026)

- **Sits in front of CTAP** — every CTAP request passes through this service first. `http.proxy_host` shows the internal upstream it forwards to, e.g.
  `ctap1993-ctap-cue-uxapi.ivp.svc.cluster.local:8000`.
- `service.name` = `session-guard`, `service.namespace` = `synamedia-streaming`, `instrumentation.name` = `session-guard-tracer`
- **`span.kind` = `internal`** (not `server`, despite being the actual network-facing hop) — don't filter for `span.kind == "server"` when querying this service, you'll get zero results.
- **Span name = the full URL path** (e.g. `/ctap/v1/household/me/devices`), not a templated route — group by `http.route` (also the full URL here, not templated like CTAP's) if you need per-endpoint
  breakdowns.
- ⚠️ **Span duration (`end-time-micros` − `start-time-micros`) is near-zero (~1-2ms observed)** — this span does NOT represent the real request lifetime, likely just an access-log-style emission after
  the fact. **Do not use `spans latency`/span duration on this service** — the real timing lives in two custom string tags instead:
  - **`http.request_time`** — total time session-guard itself saw the request take, in seconds as a string (e.g. `"0.088"` = 88ms)
  - **`http.upstream_response_time`** — time spent waiting on the upstream (CTAP), in seconds as a string (e.g. `"0.017"` = 17ms)
  - The **gap between these two** (`request_time` − `upstream_response_time`) is session-guard's own overhead/queueing time, isolated from CTAP.
- **Identity tags use snake_case here, unlike most other services**: `device_id` (not `deviceId`), `household_id` (not `householdId`), `client_id`, `businessunit_id` — always double-check casing per
  service, don't assume `deviceId` works everywhere.
- Other tags: `community` (e.g. `LIVE`), `device_type` (e.g. `BROWSER/PC` — same reliability caveat as `deviceType` elsewhere, don't use for platform segmentation), `http.canary`,
  `http.client_application`, `http.client_type`, `http.method`, `http.status_code`, `http.url`, `net.host.ip`, `net.peer.ip`, `error` (string `"true"/"false"`),
  `rate_limiter.name`/`rate_limiter.status`, `FCID` (present directly, unlike `sm-vod`/`households-*`)
- `sg.*`-prefixed tags: `sg.cmty_ck`, `sg.cmty_ck_update`, `sg.gzip_ratio`, `sg.no_store`, `sg.timestamp`, `sg.wsb_ck_status` — session-guard internal cookie/community-cache bookkeeping, not yet
  understood in detail, likely not relevant to latency investigations.
- `otlp.trace_id` here is a concatenation of two 16-hex-char halves (e.g. `28699d813c74ce1a` + `14039e00816bf352`) rather than a single 32-char OTel trace ID seen elsewhere — the second half matches
  Lightstep's own `trace-id`.
- `project_id` tag on this service shows `1z5vo5g2` (the Matisse/client-identity Project ID from the MTN SA default context) even inside the GO/IH platform project (`mcs-go-prod-iye9omdf-eu`) — likely
  session-guard is shared infra across products, not evidence of a cross-tenant bug.
- Reporter host names follow pattern `sg<digits>-sg-sg-<pod-suffix>` (Node.js/OTel instrumented).

### `sm-vod` (streaming session lifecycle: `POST/GET/DELETE /streamingSession`)
- `sessionId` / `session.sessionId` — format `abr-vod-<uuid>`, matches HAR's playsession IDs
- `contentId` / `session.contentId` — format `<uuid>~WLDP_WLDP<digits>` (CTAP-internal asset ID; **does not match** ticket-facing show IDs like `WLDP_47_0001000000` — always resolve the actual asset
  ID from a trace before filtering by content)
- `drmType` / `session.drmType` — e.g. `wvDrm`
- **`session.result`** — `"nok"`/presumably `"ok"` — the clearest pass/fail signal seen on any service so far (found on `POST /streamingSession/:sessionId/keepAlive`, `event=SessionMetrics`)
- `serviceDeliveryType` — e.g. `abr`
- `catalogId`, `assetDuration`, `externalPackageId`, `playbackURL`, `offerIds`, `providerId`, `keepAliveInterval`, `skipFwAllowed`/`skipRwAllowed`, `trickSpeedsFw`
- `externalTeardownReason` — e.g. `HEARTBEAT_VIOLATION` (seen on failed `GET /streamingSession/:sessionId` after session already torn down)
- Location tags: `city`, `state`, `countryCode`, `clientIp`
- Reporter service name in `service.name` = `sm-vod`

### `sm-linear` / `sm-tstv` (same `GET /streamingSession/:sessionId` shape as sm-vod, different content type)
- Same session/device/household fields as sm-vod
- **Failure signature repeatedly observed:** CTAP `DELETE /ctap/.../playsessions/:sessionId?playPosition=<near-zero>` (200 OK) → internal `fullScreen/deletePlaySession` → `GET
  /streamingSession/:sessionId` returns **404**, `reason="Session <id> not found in redis"`, `externalTeardownReason=HEARTBEAT_VIOLATION`, log
  `event=GetSessionFailed,result=failure,errorCode=404,errorText=NOT_FOUND`
- `playPosition` query param on the CTAP DELETE call is the clearest per-attempt "how far did playback get" signal (values seen: `0.043667`, `0.047445` — both near-zero, consistent with local HAR
  findings)

### `ctap` (`service.name = ctap`, k8s component `cue`)
- `sessionInfo.*` prefix carries most context: `sessionInfo.deviceId`, `sessionInfo.deviceType`, `sessionInfo.householdId`, `sessionInfo.busUnitId`, `sessionInfo.tenant`, `sessionInfo.timezone`,
  `sessionInfo.region`, `sessionInfo.userRegion`, `sessionInfo.community`, `sessionInfo.clientType`, `sessionInfo.matisseAppId`, `sessionInfo.matisseProjectId`, `sessionInfo.uiLanguage`,
  `sessionInfo.metadataLanguage`, `sessionInfo.ctapPluginsVersion`, `sessionInfo.profileType`, `sessionInfo.guestMode`
- `request.api` / `request.targetApiId` — named operation, e.g. `searchHistory`, `deletePlaySession`
- `request.service` — internal service name, e.g. `cue`
- `request.startTime` — ISO string, independent of `start-time-micros`
- **Caution:** `sessionInfo.deviceId`/`sessionInfo.householdId` can belong to a **completely different household/tenant** than the one you filtered on if your query used an OR across multiple device
  IDs — always verify `sessionInfo.householdId` matches your target before trusting a "match" (seen: an unrelated device on `sessionInfo.tenant=k`, `sessionInfo.timezone=Europe/Berlin` showing up
  under a loose OR filter)
- Named routes seen: `GET /ctap/:uxApiVersion/agg/content`, `GET /ctap/:uxApiVersion/keywords/suggest`, `GET /ctap/:uxApiVersion/searchHistory/topSearches`, `GET
  /ctap/:uxApiVersion/contentInstances/:instanceId`, `GET /ctap/:uxApiVersion/agg/recommendations/related`, `POST /ctap/:uxApiVersion/devices/me/playsessions`, `DELETE
  /ctap/:uxApiVersion/devices/me/playsessions/:sessionId`, `POST /ctap/:uxApiVersion/devices/:deviceId/settings`
- Many raw span exports show span_name as generic `GET`/`POST` rather than the templated route — the templated `http.route` tag is the reliable field, not `span-name`, when doing bulk exports

### `channellineup`
- `module = channelLineup`
- `http.target` query params: `bouquetId`, `deviceType`, `community`
- Debug logs: `getKey in mongo for key catalogueId_<bouquetId>_<deviceType>[_<community>]`
- Named route: `GET /consume/catalogs`

### `households-api`
- `entityType` (e.g. `device`), `upmSourceType` (e.g. `CTAP`), `sourceId`, `cacheByPass`
- Route pattern: `PUT /:deviceId` on `/upm/households/:householdId/devices/:deviceId`

### `households-core`
- `mongoDurationMax`/`mongoDurationMin`/`mongoQueriesCount` — perf/debug fields
- Route pattern: `PATCH /:projectName/:entityType/:entityId/:firstLevelProp` on `/households-core/<busUnitId>/device/:deviceId/preferences`

### `households-transformer`
- Route pattern: `PUT /:projectName/:entityType/:entityId/:firstLevelProp` on `/households-transformer/<busUnitId>/device/:deviceId/deviceInfo`
- Log message: `"Fill defaults for property update"`

### `households-notifications-generator`
- Route pattern: `PUT /:projectName/added` (also seen: `/updated`) on `/households-notifications-generator/<busUnitId>/added`
- Log message: `"preparing added notification, key=<uuid>"`

---

## Not yet covered

The following services appear in `knowledge/mtn-sa-service-correlation-maps.md` but do not yet have their own tag-level entry here: `vodcontent-get`, `favm`, `viewinghistory-viewing-history`, and
`tstv-capture-bc`. Filling those gaps from `vod-asset-ingestion-mapping` trace JSONs is out of scope for this task and left for a future harvest pass.

## Known noise / red herrings

- `Kinesis.PutRecords` spans with `http.status_code=400` and `exception.message="Stream events under account <account> not found."` (`ResourceNotFoundException`) appear routinely in traces (seen on
  `sm-vod`) — this is an **internal analytics-pipeline error, unrelated to playback failures**. Don't treat as evidence of the customer-facing issue.
- `deviceType=PC` tag — see "Near-universal but inconsistent shape" above; do not use for platform segmentation.

## Group-by field recommendations for future queries

- For pass/fail signal on VOD/linear/tstv playback: filter/group by `session.result` (sm-vod) or watch for the `DELETE .../playsessions?playPosition=<near-zero>` → 404
  `GetSessionFailed`/`HEARTBEAT_VIOLATION` pattern (sm-linear/sm-tstv).
- For cross-service overview: `group_by ["service", "http.status_code"]` — but note `query_timeseries`'s `group_by` pipeline has under-sampled `ctap` spans in practice vs. a raw `query_spans`/manual
  UI CSV export; cross-check both if `ctap` appears to be missing.
- Always resolve the actual CTAP-internal asset ID (`<uuid>~WLDP_WLDP<digits>`) from a real trace before filtering by a ticket-facing show ID — the two ID formats do not match directly.

## Source

Source path: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md`. Built from `get_stored_trace` pulls during the 7231547 investigation session, 14
Aug 2026; see `investigations/docs/7231547-android-secure-decoder-failure.md` there for the issue-specific narrative this fed into. The source path is read-only reference, not a shared codebase.
