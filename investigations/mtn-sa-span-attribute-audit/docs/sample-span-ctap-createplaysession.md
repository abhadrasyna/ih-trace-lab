# Sample span — ctap server, `createPlaySession` (MTN SA)

One span captured via Lightstep MCP (project `mcs-go-prod-iye9omdf-eu`, EU region), looked up directly by a user-supplied span-id/trace-id pair (`d6b8f5921fc63130` / `88eeeca909dc567a`). Like
`sample-span-ctap-server.md`, this is `ctap`'s `cue` component — but a different `request.api` (`createPlaySession` vs. `shared_content`), from a much larger trace (71 spans total, fanning out to
`households-core`, `useraction-agent`, an offers/content catalogue service, MongoDB, and Redis). This doc captures the raw single span for attribute reference and directly compares its tag set against
the existing `shared_content` sample — not an aggregate or a judgment on span health.

## Identity

| Field | Value |
| --- | --- |
| span-id (hex) | `d6b8f5921fc63130` |
| span-id (decimal) | `15472386527778451760` |
| trace-id (Lightstep, hex) | `88eeeca909dc567a` |
| trace-id (Lightstep, decimal) | `9867084044374398586` |
| otlp.trace_id | `6051c752bc10ed8788eeeca909dc567a` |
| reporter-id | `aaa7587d2ed40bd8` |
| span-name | `POST /ctap/:uxApiVersion/devices/me/playsessions` |
| is-error | `false` |

## Timing

| Field | Value |
| --- | --- |
| start-time-micros | `1791267844909000` (`2026-10-06T06:24:04.909Z`) |
| end-time-micros | `1791267845805001` (`2026-10-06T06:24:05.805001Z`) |
| duration | `896001` µs (~896 ms) |

## Tags (span attributes)

| Attribute | Value |
| --- | --- |
| FCID | `6AC49404AB15E12900000D1A` |
| http.client_ip | `41.126.55.202` |
| http.flavor | `1.1` |
| http.host | `api-iye9omdf.go.synamedia.com` |
| http.method | `POST` |
| http.request_content_length_uncompressed | `0` |
| http.route | `/ctap/:uxApiVersion/devices/me/playsessions` |
| http.scheme | `http` |
| http.status_code | `200` |
| http.status_text | `OK` |
| http.target | `/ctap/v1/devices/me/playsessions?instanceId=6edc0451-cf9c-5b71-9dad-3f8aa0151e43~axp_AXPX2026081200010003~vod&startingPosition=0` |
| http.url | `http://{http.host}{http.target}` (identical to `http.host` + `http.target` above) |
| http.user_agent | `Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36` |
| instrumentation.name | `@opentelemetry/instrumentation-http` |
| instrumentation.version | `0.219.0` |
| net.host.ip | `::ffff:10.130.24.159` |
| net.host.name | `api-iye9omdf.go.synamedia.com` |
| net.host.port | `8000` |
| net.peer.ip | `::ffff:10.130.119.241` |
| net.peer.port | `28422` |
| net.transport | `ip_tcp` |
| otlp.trace_id | `6051c752bc10ed8788eeeca909dc567a` |
| request.aReq | `1` |
| request.api | `createPlaySession` |
| request.apiType | `refapi` |
| request.bytes | `2296` |
| request.contentId | `6edc0451-cf9c-5b71-9dad-3f8aa0151e43~axp_AXPX2026081200010003` |
| request.contentType | `vod` |
| request.service | `cue` |
| request.startTime | `2026-10-06T06:24:04.910Z` |
| request.targetApiId | `createPlaySession` |
| sessionInfo.X-Forwarded-Host | `api-iye9omdf.go.synamedia.com` |
| sessionInfo.activeRequests | `1` |
| sessionInfo.amsEnabled | `true` |
| sessionInfo.api | `createPlaySession` |
| sessionInfo.appsSwimlaneItems | `false` |
| sessionInfo.avoidPPSQuery | `true` |
| sessionInfo.busUnitId | `iye9omdf` |
| sessionInfo.clientType | `00199aba-6faa-4dff-9a96-f41c5d12c80a` |
| sessionInfo.community | `LIVE` |
| sessionInfo.ctapPluginsVersion | `latest` |
| sessionInfo.deviceId | `eb4aed88d44b0fa3ad242709a89cfc8daba646d7dcbc225b645a3b9fe610a280` |
| sessionInfo.deviceType | `PC` |
| sessionInfo.guestMode | `false` |
| sessionInfo.host | `api-iye9omdf.go.synamedia.com` |
| sessionInfo.householdId | `6ylV311k0yh5SadX1IbIlDOnE7-YfCkeSNDE3Ej-Ljw7yv5bS-B_` |
| sessionInfo.masterPersonalizationFlag | `true` |
| sessionInfo.matisseAppId | `00199aba-6faa-4dff-9a96-f41c5d12c80a` |
| sessionInfo.matisseProjectId | `1z5vo5g2` |
| sessionInfo.metadataLanguage | `eng` |
| sessionInfo.originalVersionStr | `v1` |
| sessionInfo.refVersionNum | `170` |
| sessionInfo.region | `40000` |
| sessionInfo.tenant | `k` |
| sessionInfo.timezone | `Europe/Berlin` |
| sessionInfo.uiLanguage | `eng` |
| sessionInfo.userProfileId | `6ylV311k0yh5SadX1IbIlDOnE7-YfCkeSNDE3Ej-Ljw7yv5bS-B__0` |
| sessionInfo.userRegion | `22000` |
| sessionInfo.x-synamedia-businessunitid | `iye9omdf` |
| span.kind | `server` |

## Reporter (service/process attributes, from the trace's `relationships.reporters`)

| Attribute | Value |
| --- | --- |
| host.arch | `arm64` |
| host.name | `ctap2150-ctap-cue-8569f49d66-mq7nx` |
| k8s.container.name | `cue` |
| k8s.deployment.name | `ctap2150-ctap-cue` |
| k8s.namespace.name | `ivp` |
| k8s.node.name | `ip-10-130-52-109.eu-west-1.compute.internal` |
| k8s.pod.name | `ctap2150-ctap-cue-8569f49d66-mq7nx` |
| k8s.replicaset.name | `ctap2150-ctap-cue-8569f49d66` |
| lightstep.component_name | `ctap` |
| lightstep.hostname | `ctap2150-ctap-cue-8569f49d66-mq7nx` |
| lightstep.tracer | `otel` |
| lightstep.tracer_platform | `nodejs` |
| lightstep.tracer_version | `2.8.0` |
| process.command | `/opt/cisco/appserver/cue/server.js` |
| process.command_args | `["/usr/local/bin/node","-max-old-space-size=3072","/opt/cisco/appserver/cue/server.js"]` |
| process.executable.name | `/usr/local/bin/node` |
| process.executable.path | `/usr/local/bin/node` |
| process.owner | `root` |
| process.pid | `56` |
| process.runtime.description | `Node.js` |
| process.runtime.name | `nodejs` |
| process.runtime.version | `24.18.0` |
| service.instance.id | `ivp.ctap2150-ctap-cue-8569f49d66-mq7nx.cue` |
| service.name | `ctap` |
| service.namespace | `ivp` |
| service.version | `20260916132759-26.3.6-6` |
| syna.tenant | `iye9omdf` |
| telemetry.sdk.language | `nodejs` |
| telemetry.sdk.name | `opentelemetry` |
| telemetry.sdk.version | `2.8.0` |

## Comparison with `sample-span-ctap-server.md` (`shared_content` API)

Both spans are the same service/component (`ctap`'s `cue`), same `span.kind` (`server`), same `instrumentation.name`/`version`, and share 49 tag keys outright (all `http.*`/`net.*` transport tags,
`otlp.trace_id`, most `request.*` and `sessionInfo.*` session-context fields). The two tag sets diverge in exactly the way `household-device-field-naming-finding.md` already predicts:

| Only on `shared_content` (this trace's partner sample) | Only on `createPlaySession` (this span) |
| --- | --- |
| `sessionInfo.ccPackageDeviceType` | `http.request_content_length_uncompressed` |
| `sessionInfo.flavour` | `request.contentId` |
| `sessionInfo.isSharedApi` | `sessionInfo.X-Forwarded-Host` |
| `sessionInfo.logDeviceId` | `sessionInfo.amsEnabled` |
| `sessionInfo.logHouseholdId` | `sessionInfo.deviceId` |
| | `sessionInfo.host` |
| | `sessionInfo.householdId` |
| | `sessionInfo.masterPersonalizationFlag` |
| | `sessionInfo.matisseAppId` |
| | `sessionInfo.matisseProjectId` |
| | `sessionInfo.userProfileId` |

The headline confirmation: this span uses the plain `sessionInfo.deviceId`/`sessionInfo.householdId` pair, not the `log`-prefixed variant — consistent with `createPlaySession` not being one of the 3
"shared" (anonymous-catalogue) APIs (`shared_content`, `categorySpecific`, `sharedAsset`) that the finding doc identified as the sole `log`-prefixed emitters. `sessionInfo.isSharedApi` (present on the
`shared_content` sample, absent here) is further direct evidence of the same distinction — it's a literal flag for "is this a shared/anonymous-catalogue API," and it tracks exactly with which
household/device field pair that API emits. `sessionInfo.guestMode=false` here (an authenticated play-session request) is also consistent with — though per the finding doc not solely predictive of —
the non-`log` field choice.

The remaining `createPlaySession`-only fields (`sessionInfo.householdId`/`userProfileId`/`deviceId`, `sessionInfo.matisseAppId`/`matisseProjectId`, `request.contentId`) reflect that this is an
authenticated, content-specific action (starting a play session for a specific user/device/content) rather than an anonymous catalogue browse — these identity/content fields simply don't apply to
`shared_content`'s anonymous-catalogue use case.

## Notes

- This trace has 71 spans total (this `ctap` span is the root), fanning out to `households-core` (`GET /upm/households/:householdId`, `PUT /:hhId/:contentId`), `useraction-agent` (`POST
  /useraction-agent/1.0.0/event`), an offers/content-catalogue service (`GET /cp/om/bo/v{version}/offers`, `.../contents`, `GET /asset/policies`), MongoDB (`mongodb.find`/`update`/`saslStart`), and
  Redis (`hset`/`hgetall`/`setex`/`expire`/`multi`). Only this root span's own attributes and reporter are captured here — the full downstream fan-out is out of scope for this attribute-only doc.

## Provenance

- Lightstep MCP: `synamedia-mcp-hub-lightstep_lightstep-eu_get_stored_trace` (`project_id=mcs-go-prod-iye9omdf-eu`, `span_id=15472386527778451760` — decimal form of `d6b8f5921fc63130`) to retrieve the
  stored trace and this span's attributes directly from a user-supplied span-id/trace-id pair.
- Tenant context resolved via `scripts/resolve_tenant.py --system lightstep_go --tenant SA` / `config/tenants.yaml` (MTN SA → `mcs-go-prod-iye9omdf-eu`, EU region) per
  `docs/guides/tenant-resolution.md` (same resolution as the prior `sample-span-session-guard.md`/`sample-span-ctap-server.md` lookups in this session — not re-run here).
