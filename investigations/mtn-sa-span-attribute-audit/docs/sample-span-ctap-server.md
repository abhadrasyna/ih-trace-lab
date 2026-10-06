# Sample span — ctap server (MTN SA)

One span captured via Lightstep MCP (project `mcs-go-prod-iye9omdf-eu`, EU region), selected from the "Span Notebook" query `spans count | delta | filter (("service" == "ctap") && ("span.kind" ==
"server")) | group_by [], sum`. This is a raw, single-span capture for attribute reference — not an aggregate or a judgment on span health.

## Identity

| Field | Value |
| --- | --- |
| span-id (hex) | `3a7aa747500b1c08` |
| span-id (decimal) | `4213864326085942280` |
| trace-id (Lightstep, hex) | `d056555bf3f8d84a` |
| trace-id (Lightstep, decimal) | `15012280261309683786` |
| otlp.trace_id | `7b605422068ad85bd056555bf3f8d84a` |
| parent_span_guid | `3a7aa747500b1c08` (parent of this span's child `690ea095b90e0c47`; this span's own parent in-trace is the HTTP client span `5e4dffcedeca1215`) |
| reporter-id | `86d217beb4ba389f` |
| span-name | `GET /ctap/:uxApiVersion/shared/content` |
| is-error | `false` |

## Timing

| Field | Value |
| --- | --- |
| start-time-micros | `1791274206505000` (`2026-10-06T08:10:06.505Z`) |
| end-time-micros | `1791274206516272` (`2026-10-06T08:10:06.516272Z`) |
| duration | `11272` µs (~11.3 ms) |

## Tags (span attributes)

| Attribute | Value |
| --- | --- |
| FCID | `6AC4ACDE60DB492900000757` |
| http.client_ip | `197.184.113.204` |
| http.flavor | `1.1` |
| http.host | `ctap-cue-uxapi-haproxy:8000` |
| http.method | `GET` |
| http.route | `/ctap/:uxApiVersion/shared/content` |
| http.scheme | `http` |
| http.status_code | `200` |
| http.status_text | `OK` |
| http.target | `/ctap/v1/shared/content?seasonId=MNBG_47_0000301000&offset=0&limit=20&source=vod&clientToken=v:1!r:40000!ur:40000!community:LIVE!t:k!dt:PC!f:byoux!pd:byoux!ti:iye9omdf!gm:1` |
| http.url | `http://{http.host}{http.target}` (identical to `http.host` + `http.target` above; omitted verbatim here to stay within the 200-char line cap) |
| http.user_agent | `Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36` |
| instrumentation.name | `@opentelemetry/instrumentation-http` |
| instrumentation.version | `0.219.0` |
| net.host.ip | `::ffff:10.130.86.231` |
| net.host.name | `ctap-cue-uxapi-haproxy` |
| net.host.port | `8000` |
| net.peer.ip | `::ffff:10.130.183.4` |
| net.peer.port | `49916` |
| net.transport | `ip_tcp` |
| otlp.trace_id | `7b605422068ad85bd056555bf3f8d84a` |
| request.aReq | `1` |
| request.api | `shared_content` |
| request.apiType | `refapi` |
| request.bytes | `84918` |
| request.contentType | `vod` |
| request.service | `cue` |
| request.startTime | `2026-10-06T08:10:06.506Z` |
| request.targetApiId | `shared_content` |
| sessionInfo.activeRequests | `1` |
| sessionInfo.api | `shared_content` |
| sessionInfo.appsSwimlaneItems | `false` |
| sessionInfo.avoidPPSQuery | `true` |
| sessionInfo.busUnitId | `iye9omdf` |
| sessionInfo.ccPackageDeviceType | `byoux` |
| sessionInfo.clientType | `N/A` |
| sessionInfo.community | `LIVE` |
| sessionInfo.ctapPluginsVersion | `latest` |
| sessionInfo.deviceType | `PC` |
| sessionInfo.flavour | `byoux` |
| sessionInfo.guestMode | `true` |
| sessionInfo.isSharedApi | `true` |
| sessionInfo.logDeviceId | `0dfcd160-a415-4c46-97ec-d3d457a11e9d` |
| sessionInfo.logHouseholdId | `0dfcd160-a415-4c46-97ec-d3d457a11e9d` |
| sessionInfo.metadataLanguage | `eng` |
| sessionInfo.originalVersionStr | `v1` |
| sessionInfo.refVersionNum | `170` |
| sessionInfo.region | `40000` |
| sessionInfo.tenant | `k` |
| sessionInfo.timezone | `Europe/Berlin` |
| sessionInfo.uiLanguage | `eng` |
| sessionInfo.userRegion | `40000` |
| sessionInfo.x-synamedia-businessunitid | `iye9omdf` |
| span.kind | `server` |

## Reporter (service/process attributes, from the trace's `relationships.reporters`)

| Attribute | Value |
| --- | --- |
| host.arch | `arm64` |
| host.name | `ctap2185-ctap-cue-957c8468b-rkwkc` |
| k8s.container.name | `cue` |
| k8s.deployment.name | `ctap2185-ctap-cue` |
| k8s.namespace.name | `ivp` |
| k8s.node.name | `ip-10-130-69-10.eu-west-1.compute.internal` |
| k8s.pod.name | `ctap2185-ctap-cue-957c8468b-rkwkc` |
| k8s.replicaset.name | `ctap2185-ctap-cue-957c8468b` |
| lightstep.component_name | `ctap` |
| lightstep.hostname | `ctap2185-ctap-cue-957c8468b-rkwkc` |
| lightstep.tracer | `otel` |
| lightstep.tracer_platform | `nodejs` |
| lightstep.tracer_version | `2.8.0` |
| process.command | `/opt/cisco/appserver/cue/server.js` |
| process.command_args | `["/usr/local/bin/node","--max-semi-space-size=128","/opt/cisco/appserver/cue/server.js"]` |
| process.executable.name | `/usr/local/bin/node` |
| process.executable.path | `/usr/local/bin/node` |
| process.owner | `root` |
| process.pid | `56` |
| process.runtime.description | `Node.js` |
| process.runtime.name | `nodejs` |
| process.runtime.version | `24.18.0` |
| service.instance.id | `ivp.ctap2185-ctap-cue-957c8468b-rkwkc.cue` |
| service.name | `ctap` |
| service.namespace | `ivp` |
| service.version | `20260924081444-26.3.7-3` |
| syna.tenant | `iye9omdf` |
| telemetry.sdk.language | `nodejs` |
| telemetry.sdk.name | `opentelemetry` |
| telemetry.sdk.version | `2.8.0` |

## Provenance

- Lightstep MCP: `synamedia-mcp-hub-lightstep_lightstep-eu_query_spans` (filter `service == "ctap" && span.kind == "server"`, window 2026-10-06T08:00:00Z–09:30:00Z) to find a candidate span/trace ID
  pair, then `synamedia-mcp-hub-lightstep_lightstep-eu_get_stored_trace` (`trace_id=15012280261309683786`, `start_time=2026-10-06T08:11:00Z`) to retrieve the full trace and this span's attributes.
- Tenant context resolved via `scripts/resolve_tenant.py --system lightstep_go --tenant SA` / `config/tenants.yaml` (MTN SA → `mcs-go-prod-iye9omdf-eu`, EU region) per
  `docs/guides/tenant-resolution.md`.
