# Sample span — households-core server (MTN SA)

Second reference span captured via Lightstep MCP (project `mcs-go-prod-iye9omdf-eu`, EU region), looked up directly by the IDs given: `lightstep.span_id: 06a589c55097a977`, `lightstep.trace_id:
d49b0d3e70352ccc`. Raw single-span capture for attribute reference — not an aggregate or a judgment on span health.

## Identity

| Field | Value |
| --- | --- |
| span-id (hex) | `06a589c55097a977` |
| span-id (decimal) | `478940415938505079` |
| trace-id (Lightstep, hex) | `d49b0d3e70352ccc` |
| trace-id (Lightstep, decimal) | `15319853119252540620` |
| otlp.trace_id | `897c5fbec2e12636d49b0d3e70352ccc` |
| reporter-id | `3768d555108d5be4` |
| span-name | `POST /ctap/:uxApiVersion/userProfiles/` |
| is-error | `false` |

## Timing

| Field | Value |
| --- | --- |
| start-time-micros | `1791268786185000` (`2026-10-06T06:39:46.185Z`) |
| end-time-micros | `1791268789243716` (`2026-10-06T06:39:49.243716Z`) |
| duration | `3058716` µs (~3.06 s) |

## Tags (span attributes)

| Attribute | Value |
| --- | --- |
| FCID | `6AC497B2EB4EA229000010AE` |
| http.client_ip | `41.126.238.120` |
| http.flavor | `1.1` |
| http.host | `api-iye9omdf.go.synamedia.com` |
| http.method | `POST` |
| http.request_content_length_uncompressed | `121` |
| http.route | `/ctap/:uxApiVersion/userProfiles/` |
| http.scheme | `http` |
| http.status_code | `201` |
| http.status_text | `CREATED` |
| http.target | `/ctap/v1/userProfiles` |
| http.url | `http://api-iye9omdf.go.synamedia.com/ctap/v1/userProfiles` |
| http.user_agent | `Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36` |
| instrumentation.name | `@opentelemetry/instrumentation-http` |
| instrumentation.version | `0.219.0` |
| net.host.ip | `::ffff:10.130.98.180` |
| net.host.name | `api-iye9omdf.go.synamedia.com` |
| net.host.port | `8000` |
| net.peer.ip | `::ffff:10.130.107.48` |
| net.peer.port | `14672` |
| net.transport | `ip_tcp` |
| otlp.trace_id | `897c5fbec2e12636d49b0d3e70352ccc` |
| request.aReq | `1` |
| request.api | `addUserProfile` |
| request.apiType | `refapi` |
| request.bytes | `488` |
| request.service | `cue` |
| request.startTime | `2026-10-06T06:39:46.186Z` |
| request.targetApiId | `addUserProfile` |
| sessionInfo.X-Forwarded-Host | `api-iye9omdf.go.synamedia.com` |
| sessionInfo.activeRequests | `1` |
| sessionInfo.amsEnabled | `true` |
| sessionInfo.api | `addUserProfile` |
| sessionInfo.appsSwimlaneItems | `false` |
| sessionInfo.avoidPPSQuery | `true` |
| sessionInfo.busUnitId | `iye9omdf` |
| sessionInfo.clientType | `00199aba-6faa-4dff-9a96-f41c5d12c80a` |
| sessionInfo.community | `LIVE` |
| sessionInfo.ctapPluginsVersion | `latest` |
| sessionInfo.deviceId | `626d913f77753a0c707470fd7719a0e1e8c39c3e19fdb81981e4a700a8ce08af` |
| sessionInfo.deviceType | `PC` |
| sessionInfo.guestMode | `false` |
| sessionInfo.host | `api-iye9omdf.go.synamedia.com` |
| sessionInfo.householdId | `pbilODrRBkQiScfyN7-4kXdhBRIR9uacUaIsWQegHZw4Vgq6IlOi` |
| sessionInfo.masterPersonalizationFlag | `true` |
| sessionInfo.matisseProjectId | `1z5vo5g2` |
| sessionInfo.metadataLanguage | `eng` |
| sessionInfo.originalVersionStr | `v1` |
| sessionInfo.refVersionNum | `170` |
| sessionInfo.region | `40000` |
| sessionInfo.tenant | `k` |
| sessionInfo.timezone | `Europe/Berlin` |
| sessionInfo.uiLanguage | `eng` |
| sessionInfo.userProfileId | `pbilODrRBkQiScfyN7-4kXdhBRIR9uacUaIsWQegHZw4Vgq6IlOi_0` |
| sessionInfo.userRegion | `22000` |
| sessionInfo.x-synamedia-businessunitid | `iye9omdf` |
| span.kind | `server` |

## Reporter (service/process attributes, from the trace's `relationships.reporters`)

| Attribute | Value |
| --- | --- |
| host.arch | `arm64` |
| host.name | `ctap2150-ctap-cue-59f75784db-c8f22` |
| k8s.container.name | `cue` |
| k8s.deployment.name | `ctap2150-ctap-cue` |
| k8s.namespace.name | `ivp` |
| k8s.node.name | `ip-10-130-95-80.eu-west-1.compute.internal` |
| k8s.pod.name | `ctap2150-ctap-cue-59f75784db-c8f22` |
| k8s.replicaset.name | `ctap2150-ctap-cue-59f75784db` |
| lightstep.component_name | `ctap` |
| lightstep.hostname | `ctap2150-ctap-cue-59f75784db-c8f22` |
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
| service.instance.id | `ivp.ctap2150-ctap-cue-59f75784db-c8f22.cue` |
| service.name | `ctap` |
| service.namespace | `ivp` |
| service.version | `20260916132759-26.3.6-6` |
| syna.tenant | `iye9omdf` |
| telemetry.sdk.language | `nodejs` |
| telemetry.sdk.name | `opentelemetry` |
| telemetry.sdk.version | `2.8.0` |

## Comparison against `sample-span-ctap-server.md`

Compares this span's 54 tags against the earlier `GET /ctap/:uxApiVersion/shared/content` span's 54 tags (reporter attributes excluded — those describe the pod/process, not the span itself, and differ
trivially by pod name).

| Category | Count |
| --- | --- |
| Common keys (both spans) | 48 |
| Only in `sample-span-ctap-server.md` (span 1) | 6 |
| Only in this span (span 2) | 9 |
| Common keys with different values | 22 |
| Common keys with identical values | 26 |

**Total differing properties: 37** (6 + 9 + 22 — present-in-one-only keys plus common keys whose values disagree). The two spans represent different API calls (`shared_content` VOD-catalogue read on
`ctap` vs. `addUserProfile` write on `households-core`), so divergence is in device/session/request-specific fields and endpoint plumbing, while instrumentation/runtime and most `sessionInfo.*`
session-shape fields stay identical.

Only in `sample-span-ctap-server.md` (span 1): `request.contentType`, `sessionInfo.ccPackageDeviceType`, `sessionInfo.flavour`, `sessionInfo.isSharedApi`, `sessionInfo.logDeviceId`,
`sessionInfo.logHouseholdId`.

Only in this span (span 2): `http.request_content_length_uncompressed`, `sessionInfo.X-Forwarded-Host`, `sessionInfo.amsEnabled`, `sessionInfo.deviceId`, `sessionInfo.host`, `sessionInfo.householdId`,
`sessionInfo.masterPersonalizationFlag`, `sessionInfo.matisseProjectId`, `sessionInfo.userProfileId`.

Common keys with different values: `FCID`, `http.client_ip`, `http.host`, `http.method`, `http.route`, `http.status_code`, `http.status_text`, `http.target`, `http.url`, `net.host.ip`,
`net.host.name`, `net.peer.ip`, `net.peer.port`, `otlp.trace_id`, `request.api`, `request.bytes`, `request.startTime`, `request.targetApiId`, `sessionInfo.api`, `sessionInfo.clientType`,
`sessionInfo.guestMode`, `sessionInfo.userRegion`.

Common keys with identical values: `http.flavor`, `http.scheme`, `http.user_agent`, `instrumentation.name`, `instrumentation.version`, `net.transport`, `request.aReq`, `request.apiType`,
`request.service`, `sessionInfo.activeRequests`, `sessionInfo.appsSwimlaneItems`, `sessionInfo.avoidPPSQuery`, `sessionInfo.busUnitId`, `sessionInfo.community`, `sessionInfo.ctapPluginsVersion`,
`sessionInfo.deviceType`, `sessionInfo.metadataLanguage`, `sessionInfo.originalVersionStr`, `sessionInfo.refVersionNum`, `sessionInfo.region`, `sessionInfo.tenant`, `sessionInfo.timezone`,
`sessionInfo.uiLanguage`, `sessionInfo.x-synamedia-businessunitid`, `span.kind`.

## Provenance

- `synamedia-mcp-hub-lightstep_lightstep-eu_query_spans` (filter `"lightstep.trace_id" == "15319853119252540620"`, window 2026-10-05T00:00:00Z–2026-10-06T10:00:00Z) to locate the span's timestamp,
  then `synamedia-mcp-hub-lightstep_lightstep-eu_get_stored_trace` (`trace_id=d49b0d3e70352ccc`, `start_time=2026-10-06T06:41:00Z`) to retrieve the full trace and this span's attributes.
- Tenant context: MTN SA → `mcs-go-prod-iye9omdf-eu` (EU region), per `config/tenants.yaml` / `docs/guides/tenant-resolution.md` (same project as `sample-span-ctap-server.md`).
