# Knowledge: MTN SA Production — Service Correlation Maps (GO/IH, Matisse, mDRM)

> Derived from Lightstep's **service diagram** feature (real call-graph built from observed spans, not a naming convention), run against all three MTN SA production Lightstep projects: GO/IH platform
> (`mcs-go-prod-iye9omdf-eu`, EU — §1-5), Matisse (`mcs-matisse-production-eu`, EU — §6), and mDRM (`mcs-mdrm-production`, **US** — §7). Snapshots taken 2026-07-18. This file captures the reusable
> maps + method so future investigations don't have to regenerate them from scratch. Read this first when: tracing which services a request could have touched, scoping a blast radius for an incident,
> or deciding whether FCID/Kinesis-based tracing is needed instead of a service diagram.

---

## 1. How this map was built (repeatable method)

Lightstep's snapshot + service-diagram tools build a **live call graph** from actual trace data in a time window — not documentation, actual observed `from → to` service calls.

```
1. list_services(project_id) → get the full service name list
2. create_snapshot(project_id, {
     data: { type: "snapshot", attributes: {
       name, oldest_time, youngest_time,
       query: 'service IN ("svc1", "svc2", ...)'
     }}
   })
   → returns { id: snapshot_id }
3. get_service_diagram(project_id, snapshot_id)
   → returns { service-diagram: { edges: { id: {from, to} } } }
```

**Gotchas:**
- `create_snapshot`'s `snapshot` payload must be wrapped exactly as `{"data": {"type": "snapshot", "attributes": {...}}}` — passing `query`/`oldest_time`/`youngest_time` as top-level or under a bare
  `attributes` key (without the `data`/`type` wrapper) fails with a misleading `"query argument is required"` error even when `query` is present.
- `query` uses Lightstep's legacy UQL syntax: `service IN ("a", "b", ...)` — list every service name explicitly; there's no wildcard/"all services" shorthand confirmed working.
- Widening the time window (tested 1h → 24h → 7d) barely changes the result — see §3. Don't assume a longer window will surface much more; the gap is structural, not a sampling artifact.

## 2. Full platform inventory

**117 services** total in `mcs-go-prod-iye9omdf-eu` as of 2026-07-18 (via `list_services`). Only **~48** ever appear as an edge endpoint in the service diagram (see §3) — the rest are invisible to
this method (see §4 for why, and what to use instead).

## 3. Observed correlation graph (7-day window, stable vs 24h/1h)

```
ctap → brooklyn-api-proxy, channellineup, favm, go-metering-bundle,
       households-api, mostviewed-mostviewedget, offers-ombo, pcpe,
       recommendrelated, search_aggregator, sm-tstv, sm-vod,
       tstv-capture-bc, useraction-agent, viewinghistory-viewing-history,
       vodcontent-get

sm-vod → evaluatepolicy, vodcontent-get
sm-linear → channellineup
evaluatepolicy → gls, ipom, offers-ombo, channellineup, households-api
gls → iplookup, brooklyn-api-proxy
sg-websessionbuilder → gls, households-api

households-api → households-core, households-filters, households-datamodels,
                  households-transformer, households-notifications-generator
households-core → households-config
households-filters → households-config, households-indexer
households-notifications-generator → households-config
households-transformer / households-datamodels-worker → households-datamodels
households-cleanup → households-query
infrabridge-householdsnotifications → households-notifications

search_ingest → search_aggregator → search_history, search_indexer
lastviewedchannel, lockedchannels → channellineup
vodOfferIngest → offers-ombo
ingestimages-vod → brooklyn-api-proxy, vodingestsystem-vodpublisher
vodingestsystem-vodpublisher → vodingestsystem-vodisconfig
vodingestsystem-vodpackagerouter → brooklyn-api-proxy
tstv-catchup-publisher → tstv-capture-bc
brooklyn-metrics-bundle, contentcuration-db → brooklyn-api-proxy
```

**Read of the graph:**
- **`ctap`** is the dominant entry-point hub — 16 direct downstream services. Matches its role as the primary session/playback orchestrator API.
- **`channellineup`** is the most shared dependency (5+ distinct callers) — treat it as a common single-point-of-failure for lookups.
- **`households-*`** is its own internal cluster (`api → core/filters/datamodels/transformer → config/indexer`), only loosely joined to the rest via `evaluatepolicy` / `sg-websessionbuilder`.
- **`brooklyn-api-proxy`** looks like a shared telemetry/logging sink — many unrelated services call it, it calls out to nothing.

## 4. Coverage gap: ~69 services show no edges — why, and what to use instead

Confirmed by comparing 1h / 24h / 7d snapshots — the same ~48 services show up regardless of window length. This is **not** a sampling gap, it's structural: the service-diagram method only surfaces
**server-to-server calls captured as linked spans**. It misses:

| Category | Example services | Why invisible here |
|---|---|---|
| UI/frontend-only (browser-invoked) | `opshubgo-*ui*` (10), `synaopshub-*` (3) | Called from browsers, not from other backend services |
| Batch/cron jobs | `dvrlib-*` (4), `planner-*` (7), `maxmindingest`, `useraction-ingest`, `vodistracker-archiver` | No live cross-service call captured in the window |
<!-- lint-ignore-length -->
| Client/gateway-invoked leaves, or async (queue/Kinesis) fanout | `purchase`, `purchaseoptions`, `session-guard`, `schedule-*`, `recommend*`, `ta-useractions`, `connection-info-*`, `go-mdrmfe*`, `goexport-*`, `business-reports-*`, `rsu`, `vodorchestrator`, `boa`, `gosrm`, `operateoffers`, `clevertapexporter`, `contentcuration-curation`/`report`, `linearcuration`, `vodistracker-api`, `useraction-playsession`, `vodcontent-ingest`, `viewinghistory-series-discovery`, `tstv-capture-service`/`janitor`, `infrabridge-haproxy2consul`/`pod2consul`, `quickstart-quickstart` | Invoked directly by client apps/API-gateway/CDN with no further synchronous backend fanout, or fanout happens via an async mechanism (queue/Kinesis) that doesn't produce a linked parent-child span |

**If a service you need is in the "no edges" set, don't conclude it has no dependencies** — fall back to:
- **FCID-based request tracing** (see `AGENTS.md` → Debugging Workflow) — pick one real request that touched the service and filter `attribute.request.FCID == "<id>"` across projects to see everything
  it actually called for that request.
- **Kinesis/queue-consumer correlation** — see `investigations/instructions/kinesis-stream-analysis.md` — for services fed by async streams instead of direct calls.

## 5. Regenerating / extending this map

- Re-run the method in §1 if investigating a specific incident's blast radius, or periodically (e.g. quarterly) to catch architecture drift — update this file rather than letting a stale copy linger.
- To go deeper on a specific "no edges" service, scope `query` to just that service name (e.g. `service IN ("session-guard")`) with a longer window — a single-service query may surface edges a broad
  multi-service query misses due to Lightstep's own sampling/query limits.
- Source snapshots (as of this writing): `5ssk9sw0BpfXU` (1h, ctap-scoped), `HgEWOIY0BpfXU` (24h, full 117-service query), `2dI8cci0Bpeha` (7d, full 117-service query) — all in
  `mcs-go-prod-iye9omdf-eu`. `BrFIWXa0Bpeha` (7d, Matisse, §6) in `mcs-matisse-production-eu`. `LNx7PIy0BoZE0` (7d, mDRM, §7) in `mcs-mdrm-production` (US). Snapshots may expire; treat the graphs
  above, not the snapshot IDs, as the durable artifact.

## 6. Companion result: `mcs-matisse-production-eu` — same method, deliberately sparse

Ran the identical method (§1) against Matisse (7d window, snapshot `BrFIWXa0Bpeha`). Recorded here so it isn't re-run and mis-read as a bug:

- **7 services total** (`Accounts`, `Backup`, `Client Identity Management`, `Client Identity OAuth`, `Lambda Utils Layer`, `Products`, `Products Reporting`); only **5 appeared as graph nodes at all**
  (`Backup`, `Products` had zero call-graph presence).
- **Only 1 edge:** `Accounts → Products Reporting`. Everything else (`Client Identity Management`, `Client Identity OAuth`, `Lambda Utils Layer`) is isolated — no in/out edges.

**This is architecture, not a data gap:** Matisse is Lambda-based (API Gateway/Auth0-fronted), so most services are invoked directly by external clients with no further synchronous same-project
backend fanout to capture. `Client Identity Management`/`OAuth`'s real dependency is **Auth0**, which is external and unmonitored by this Lightstep project — invisible to a same-project service
diagram regardless of window length.

**Takeaway:** don't use the service-diagram method for Matisse correlation. Use cross-project FCID/token-claim tracing instead — a client-identity token flows from Matisse
(`mcs-matisse-production-eu`, tenant `rxviifsu`) into the GO/IH platform (`iye9omdf`) and mDRM (`qfrtzlcj`) tenants in a single user session; see the "Default Investigation Context — MTN SA
Production" table in `AGENTS.md` for the three-project cross-reference pattern.

## 7. `mcs-mdrm-production` (US region) — real internal chain, unlike Matisse

Ran the same method (§1) against mDRM, **US region** (`app.lightstep.com`, not `-eu` — mDRM has no EU project, per `AGENTS.md`'s default context table). 7-day window, snapshot `LNx7PIy0BoZE0`.

**19 services total; 16 active (19 edges)** — unlike Matisse, this is a coherent internal request-flow chain, not a sparse Lambda-leaf set:

```
health-check → client-licensing-ingress, content-key-generator-ingress,
               license-fe-ingress

client-licensing-ingress → authorization-token-service, cert-server,
                            mdrm-rate-limit, session-state-enforcer

license-fe-ingress → mdrm-rate-limit, session-state-enforcer

session-state-enforcer → authorization-token-service, license-request-manager

license-request-manager → content-key-generator, ksm-mt, license-generator-proxy

license-generator-proxy → fairplay-license-generator, playready,
                           widevine-license-generator

content-key-generator-ingress → content-key-generator, content-key-proxy
```

**Read as a license-request flow:**
1. `client-licensing-ingress` / `license-fe-ingress` are the entry points (both polled by `health-check`).
2. Requests pass through `mdrm-rate-limit` and `session-state-enforcer` (throttling + auth gate).
3. `session-state-enforcer` → `authorization-token-service` (token validation) and → `license-request-manager` (core orchestrator).
4. `license-request-manager` fans out to `content-key-generator`, `ksm-mt` (key management), and `license-generator-proxy`.
5. `license-generator-proxy` branches by DRM scheme: `fairplay-license-generator`, `playready`, `widevine-license-generator`.

**2 isolated nodes (no edges in this window):** `ccs`, `license-fe-authorizer` — same caveat as elsewhere in this file: could be low traffic or a client/gateway-invoked leaf, not necessarily zero
dependencies. Re-run a single-service-scoped query (§5) to check before concluding either way.

**Why this project's graph is so much richer than Matisse's:** mDRM is a synchronous internal microservice chain (ingress → auth/rate-limit → orchestrator → key/license generators), all within one
Lightstep project — exactly the shape the service-diagram method is built to capture. Matisse's Lambda/API-Gateway/Auth0-fronted architecture is the opposite case (§6). When guessing whether this
method will be useful for a new project, the deciding factor is: does this project's own services call *each other* synchronously, or does each service mostly talk to something external/unmonitored?

