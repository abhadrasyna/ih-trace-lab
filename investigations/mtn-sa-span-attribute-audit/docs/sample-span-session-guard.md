# Sample span — session-guard (MTN SA)

One span captured via Lightstep MCP (project `mcs-go-prod-iye9omdf-eu`, EU region), looked up directly by the user-supplied span-id/trace-id pair (`bd9b8d3fd0cc2ad1` / `01d79c2feaea8b4d`). This span
turned out to belong to the `session-guard` service, not `ctap` — captured here as a raw, single-span reference, not an aggregate or a judgment on span health.

## Identity

| Field | Value |
| --- | --- |
| span-id (hex) | `bd9b8d3fd0cc2ad1` |
| span-id (decimal) | `13662669199784028881` |
| trace-id (Lightstep, hex) | `01d79c2feaea8b4d` |
| trace-id (Lightstep, decimal) | `132746443649354573` |
| otlp.trace_id | `5baaee6d4dabdd8d01d79c2feaea8b4d` |
| reporter-id | `30d7f737443ed217` |
| span-name | `/ctap/v1/agg/content` |
| is-error | `false` |

## Timing

| Field | Value |
| --- | --- |
| start-time-micros | `1791194221387000` (`2026-10-05T09:57:01.387Z`) |
| end-time-micros | `1791194221388190` (`2026-10-05T09:57:01.388190Z`) |
| duration | `1190` µs (~1.2 ms) |

## Tags (span attributes)

| Attribute | Value |
| --- | --- |
| FCID | `6AC3746D7A81F729000025BE` |
| businessunit_id | `iye9omdf` |
| client_id | `-` |
| community | `LIVE` |
| device_id | `1716758498504e5cc62969237b2d883d56b19e3374209d12d5fa8c2a474da4a2` |
| device_type | `BROWSER/PC` |
| error | `false` |
| household_id | `mKg5FvvXSPG63ZT3dBsL0U6bf_R6AfMcZfFNnkeshBtLT5CX5FPt` |
| http.canary | `false` |
| http.client_application | `00199aba-6faa-4dff-9a96-f41c5d12c80a` |
| http.client_type | `00199aba-6faa-4dff-9a96-f41c5d12c80a` |
| http.method | `GET` |
| http.proxy_host | `ctap2150-ctap-cue-uxapi.ivp.svc.cluster.local:8000` |
| http.request_time | `0.026` |
| http.response_content_length | `34` |
| http.route | `https://api-iye9omdf.go.synamedia.com/ctap/v1/agg/content` |
| http.status_code | `200` |
| http.upstream_response_time | `0.022` |
| http.url | `https://api-iye9omdf.go.synamedia.com/ctap/v1/agg/content?q=Education&limit=20&source=ltv` |
| instrumentation.name | `session-guard-tracer` |
| net.host.ip | `172.20.177.38:8000` |
| net.peer.ip | `18.68.28.47` |
| otlp.trace_id | `5baaee6d4dabdd8d01d79c2feaea8b4d` |
| project_id | `1z5vo5g2` |
| rate_limiter.name | `NONE` |
| rate_limiter.status | `NONE` |
| sg.cmty_ck | `1` |
| sg.cmty_ck_update | `0` |
| sg.gzip_ratio | `-` |
| sg.no_store | `-` |
| sg.timestamp | `2026-10-05T09:57:01+00:00` |
| sg.wsb_ck_status | `VALID` |
| service.name | `session-guard` |
| service.namespace | `synamedia-streaming` |
| span.kind | `internal` |

## Reporter (service/process attributes, from the trace's `relationships.reporters`)

| Attribute | Value |
| --- | --- |
| host.arch | `amd64` |
| host.name | `sg2139-sg-sg-79fb655ddb-qwgnp` |
| lightstep.component_name | `session-guard` |
| lightstep.hostname | `sg2139-sg-sg-79fb655ddb-qwgnp` |
| lightstep.tracer | `otel` |
| lightstep.tracer_platform | `nodejs` |
| lightstep.tracer_version | `1.30.1` |
| process.command | `/app/index.js` |
| process.command_args | `["/usr/local/bin/node","--max-semi-space-size=64","/app/index.js","--service-name=session-guard","--span-server-port=8081"]` |
| process.executable.name | `/usr/local/bin/node` |
| process.executable.path | `/usr/local/bin/node` |
| process.owner | `root` |
| process.pid | `8` |
| process.runtime.description | `Node.js` |
| process.runtime.name | `nodejs` |
| process.runtime.version | `24.14.0` |
| service.name | `session-guard` |
| telemetry.sdk.language | `nodejs` |
| telemetry.sdk.name | `opentelemetry` |
| telemetry.sdk.version | `1.30.1` |

## Notes

- Only one span and one reporter came back for this trace-id/span-id pair — no parent/child spans were present in the `get_stored_trace` response, so this trace does not show the full cross-service
  hop (e.g. into `ctap`) that the `http.route` tag (`.../ctap/v1/agg/content`) might suggest.
- Unlike the `ctap-server` sample, this span's tag set uses flat snake_case keys (`household_id`, `device_id`, `businessunit_id`) rather than the `sessionInfo.*` namespaced keys seen on the ctap-side
  spans — consistent with the broader household/device field-naming inconsistency already tracked in `household-device-field-naming-finding.md`.

## Provenance

- Lightstep MCP: `synamedia-mcp-hub-lightstep_lightstep-eu_get_stored_trace` (`project_id=mcs-go-prod-iye9omdf-eu`, `span_id=13662669199784028881` — decimal form of `bd9b8d3fd0cc2ad1`) to retrieve the
  stored trace and this span's attributes directly from a user-supplied span-id/trace-id pair.
- Tenant context resolved via `scripts/resolve_tenant.py --system lightstep_go --tenant SA` / `config/tenants.yaml` (MTN SA → `mcs-go-prod-iye9omdf-eu`, EU region) per
  `docs/guides/tenant-resolution.md`.
