# Knowledge: MTN SA Lightstep Query Templates

## Read this first when

Consult this before writing a new Lightstep TQL query for an MTN SA investigation, so you can reuse an established query shape instead of guessing syntax. See
`knowledge/mtn-sa-lightstep-span-attributes-by-service.md` for which services expose which tag names.

---

## "Big Picture" — Service × HTTP Status × Session Result

**Purpose:** one query to get a cross-service overview of everything a device touched in a time window, broken down by service, HTTP outcome, and (where available) the `session.result` pass/fail
signal — a starting point before drilling into any single service/trace.

**Why OR across `deviceId` and `sessionInfo.deviceId`:** most services (`sm-vod`, `sm-linear`, `sm-tstv`, `channellineup`, `households-*`) tag the device as a plain `deviceId` attribute, but `ctap`
tags it as `sessionInfo.deviceId` — a query filtering only on `deviceId` will **silently miss all ctap spans**. OR-ing both field names in one filter catches both.

```
spans count | delta
| filter (deviceId == "<DEVICE_ID>" || sessionInfo.deviceId == "<DEVICE_ID>")
| group_by ["service", "http.status_code", "session.result"], sum
```

Tool: `query_timeseries`. Time window: RFC3339 UTC, sized to the investigation (widen beyond the reported repro time if a same-signature failure might recur outside it — seen happening 10+ hours later
in one investigation).

**Note:** if you need to compare **two different devices/households** in one query (e.g. cross-checking whether a symptom is device-specific or tenant-wide), put each device's ID under whichever field
name matches its own traffic pattern — don't assume both devices use the same field. Always confirm via `sessionInfo.householdId`/`householdId` in a follow-up `get_stored_trace` that a returned span
actually belongs to the household you intended — a loose OR filter can pull in a completely unrelated household/tenant's traffic if the wrong ID is used in either clause.

**Save exports as:** `investigations/data/<Applause ID>/lightstep/big-picture-service-status-result.csv`

---

## "sm-vod Session Inventory by Device"

**Purpose:** enumerate every `sm-vod` streaming session a device touched in a window, with full session/content context and outcome — a per-session inventory to cross-check against HAR-derived session
IDs (the `sessions` subcommand of `scripts/analyze_har.py`) or to spot which specific sessions/content failed.

```
spans count | delta
| filter service == "sm-vod"
    && deviceId == "<DEVICE_ID>"
| group_by ["householdId", "deviceId", "session.clientIp", "sessionId", "http.status_code", "contentId", "externalPackageId", "lightstep.trace_id", "playbackURL"], sum
```

Tool: `query_timeseries`. Note `http.status_code` gives pass/fail signal per session; `session.result` (see Big Picture template) is a narrower field only present on some event types (e.g.
`keepAlive`) — add it too if you need that specific tag.

**Save exports as:** `investigations/data/<Applause ID>/lightstep/smvod-sessions-by-content.csv`

---

## Latency templates (established during issue 7231763, 14 Aug 2026)

**Purpose:** the "Big Picture"/"sm-vod Session Inventory" templates above use `spans count | delta ..., sum` — good for pass/fail signal, useless for **latency** investigations (buffering, slow start,
resume delay). These use `spans latency` and a `| point percentile(...)` stage instead to get p50/p95/p99 span duration per group. Confirmed working syntax against `mcs-go-prod-iye9omdf-eu` — use this
exact shape, not `metric-query` percentile syntax (that was guessed and never validated).

### CTAP Route Latency Percentiles (by device)

```
spans latency
| delta
| filter service == "ctap"
    && sessionInfo.deviceId == "<DEVICE_ID>"
    && span.kind == "server"
| group_by ["http.route", "request.api", "http.status_code"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```

**Save exports as:** `investigations/data/<Applause ID>/lightstep/ctap-route-latency-percentiles.csv`

### Cross-Service Latency Big Picture

```
spans latency
| delta
| filter (deviceId == "<DEVICE_ID>" || sessionInfo.deviceId == "<DEVICE_ID>")
| group_by ["service", "http.route"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```

**Save exports as:** `investigations/data/<Applause ID>/lightstep/big-picture-service-route-latency.csv`

### Playsessions Call Latency Isolation

Targeted at isolating one route's operation-level duration (e.g. to compare resume vs. fresh-play `createPlaySession` calls) rather than averaging across all CTAP routes.

```
spans latency
| delta
| filter service == "ctap"
    && sessionInfo.deviceId == "<DEVICE_ID>"
    && http.route == "/ctap/:uxApiVersion/devices/me/playsessions"
| group_by ["request.api"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```

**Save exports as:** `investigations/data/<Applause ID>/lightstep/playsessions-latency-by-operation.csv`

**Caveat learned from 7231763:** CTAP server-side span duration can be **much lower** than the client-perceived HAR round-trip time for the same call (seen: 187-567ms server-side vs. 2.75s HAR `wait`
phase for a resume `playsessions` call). If server-side latency looks fine but the client still shows a large delay, check the HAR's `timings` breakdown (`dns`/`ssl`/`connect`/`wait`) next — a `-1` on
`dns`/`ssl`/`connect` means a warm/reused connection (rules out new-handshake causes), and if this is a Service-Worker-fronted app, HAR timings may be populated by `_worker*` fields
(`_workerFetchStart`→`_workerRespondWithSettled`) rather than raw network timing — the gap can include client-side SW overhead, not just network transit.

**Notebook used:** "Latency Investigation" (`mcs-go-prod-iye9omdf-eu`, separate from the "Applause investigation" notebook which uses the count-based templates above).

### Exact request trace-pull via FCID (client-send → server-receive → server-respond → client-receive)

**Purpose:** the aggregate latency queries above show *whether* a route is slow overall, but not *why* one specific request was slow. To pin down exactly where time is spent for one HAR-captured
request, pull its real distributed trace using the `flow_context` (FCID) value from that request's **response headers** (not a query param — confirmed present on `ctap` responses even when not
directly queryable as a span tag on `sm-vod`/`households-*`, see "Near-universal but inconsistent shape" above).

1. `query_spans` (not a saved TQL chart — this is a one-off MCP tool call, not a notebook query):
   ```
   uql_filter: FCID == "<FCID_FROM_HAR_RESPONSE_HEADER>"
   oldest_time / youngest_time: narrow window around the HAR request's timestamp
   ```
Returns matching `lightstep.span_id`/`lightstep.trace_id` pairs.
2. `get_stored_trace` with that `trace_id` — returns every span in the trace with `start-time-micros`/`end-time-micros`. Filter for the `span-name` matching your route (e.g. `POST
   /ctap/:uxApiVersion/devices/me/playsessions`, `span.kind == "server"`) to get the exact CTAP receive/respond timestamps, then diff against the HAR's `startedDateTime`/`time` to see how much delay
   happened **before** the request reached CTAP vs. **inside** CTAP processing.

**Confirmed finding using this technique (issue 7231763):** a resume `playsessions` call took 2755.8ms round-trip per the HAR, but the CTAP server span itself only took 337.6ms — the other ~2.4s
occurred *before* CTAP even received the request (network/edge transit, e.g. through CloudFront), not inside CTAP or a client-side Service Worker. This technique is much more precise than reading HAR
`timings` alone, since it separates true CTAP processing time from everything upstream of it.

---

### session-guard Request vs. Upstream Time (by device)

**Purpose:** `session-guard`'s span duration is meaningless (~1-2ms, see `knowledge/mtn-sa-lightstep-span-attributes-by-service.md`) — the real timing lives in its
`http.request_time`/`http.upstream_response_time` string tags. This query lists every session-guard-observed request for a device with both values side by side, so `request_time -
upstream_response_time` can be computed per request (session-guard's own overhead) and compared against the CTAP server-span duration and the HAR client round-trip time for the same `FCID` — the
three-way comparison is what proves whether a delay is upstream of session-guard (network/CDN) or inside it.

```
spans count
| delta
| filter service.name == "session-guard"
    && device_id == "<DEVICE_ID>"
| group_by ["http.route", "http.status_code", "http.request_time", "http.upstream_response_time", "FCID"], sum
```

Tool: `query_timeseries`. Note the field names are **snake_case** (`device_id`, not `deviceId`) and the filter key is `service.name`, not `service` — different convention than every other service
documented so far, easy to get zero results if you copy another template's casing.

**Confirmed finding (issue 7231763, resume `playsessions` call, FCID `6A7C73ACB717BF290000003C`):** session-guard's own total request_time was 344ms (338ms of which was CTAP upstream) — session-guard
is not the source of the ~2.4s gap seen between the HAR client-send timestamp and CTAP's server-span start. The delay is upstream of session-guard (network/CDN/edge), not inside any
Lightstep-instrumented service.

**Save exports as:** `investigations/data/<Applause ID>/lightstep/session-guard-request-vs-upstream.csv`

---

## `go-mdrmfe` EU Latency Percentiles (by device/content) — established during issue 7233017, 14 Aug 2026

**Purpose:** check DRM/Widevine license backend health for a device — `go-mdrmfe` is the EU proxy in front of the actual US mDRM license generation (see
`investigations/instructions/drm-cross-region-investigation.md`). Server-side span duration here can be **dramatically lower** than the HAR-observed client wait (confirmed: up to 50x gap, 40ms
server-side vs. 1959ms client-observed) — a low `go-mdrmfe` latency here, combined with a much higher HAR client-observed wait for the same content/session, is strong evidence the delay is network
transit to/from the edge, not the DRM backend.

```
spans latency
| delta
| filter service == "go-mdrmfe"
    && (deviceId == "<DEVICE_ID>" || request.deviceId == "<DEVICE_ID>")
| group_by ["request.contentId", "http.status_code"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```

Tool: `query_timeseries`, project `mcs-go-prod-iye9omdf-eu` (EU).

**Save exports as:** `investigations/data/<Applause ID>/lightstep/mdrmfe-eu-latency-percentiles-by-content.csv`

**Follow-up — exact trace pull to confirm the pre-/post-edge transit split:** `query_spans` (`service == "go-mdrmfe" && request.contentId == "<CONTENT_ID>"`) → `get_stored_trace` on the matched span.
Compare three timestamps: (1) HAR client-send time, (2) the `go-mdrmfe` server span's `start-time-micros` (when the EU edge actually received the request), (3) the HAR client-receive time vs. the
server span's `end-time-micros`. The two gaps ((2)-(1) and (3)-(2)-ish, i.e. HAR-receive minus server-respond) isolate transit time **into** vs. **out of** the edge, separately from `go-mdrmfe`'s own
processing (which also includes its child span to `license.global.multidrm.synamedia.com`, the actual US mDRM round-trip — confirmed healthy at ~34ms in this investigation).

**Confirmed finding (issue 7233017, Episode 2, contentId `1e1f48ec-9a15-5098-a96a-afa6af39b8e9`, trace_id `a805037f2c1ce3d87d679ff21806cc92`):** HAR client sent the license POST at 20:24:05.492Z;
`go-mdrmfe` didn't receive it until 20:24:06.787Z (**+1295ms transit in**); `go-mdrmfe`'s own processing (incl. the US mDRM round-trip) took only 35.9ms; the client didn't receive the response until
~20:24:07.451Z (**+628ms transit out**). 1295+36+628 ≈ 1959ms — accounts for essentially the entire client-observed wait. Same root-cause family as the `playsessions`-call edge-transit delay found in
issue 7231763, confirming this MTN SA network path has a recurring edge-transit latency problem, not isolated to one API route.

---

(Add more reusable templates here as they're established — e.g. a per-service error/operation breakdown, a content/show-filtered spans query, etc.)

## Source

Source path: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`. The source path is read-only reference, not a shared codebase.
