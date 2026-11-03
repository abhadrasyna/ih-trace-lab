# Lightstep querying guide

Read-first checklist before any `query_spans` / `query_timeseries` / `get_stored_trace` call. Most failed Lightstep queries in this repo came from skipping one of these docs, so `session-close` audits
that it was followed.

## Before the first query

1. Resolve the tenant: `python scripts/resolve_tenant.py ...` per `docs/guides/tenant-resolution.md`. Apply the returned `filter` when the Lightstep project is shared between opcos.
2. Read `knowledge/mtn-sa-lightstep-span-attributes-by-service.md` for the tag names and casing each service really uses.
3. Read `knowledge/mtn-sa-lightstep-query-templates.md` and `queries/lightstep/index.md`; reuse an existing template or catalog entry instead of writing TQL from scratch (see
   `docs/guides/query-catalog.md`).
4. Read the topic doc if one applies (table below).

## Topic docs

| Topic | Doc |
|---|---|
| Tool rules, identity/OAuth flow, EU/US DRM boundary | `knowledge/mtn-lightstep-identity-and-session-investigation-methodology.md` |
| Which service calls which, FCID/session join keys | `knowledge/mtn-sa-service-correlation-maps.md` |
| mDRM session to device tracing | `knowledge/mtn-sa-mdrm-session-to-device-tracing.md` |
| TimPlay/DRM cross-tenant traces | `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` |
| CDN logs vs Lightstep | `knowledge/mtn-sa-cdn-log-correlation-methodology.md` |
| Outcome and error-code meaning | `knowledge/mtn-sa-playback-outcome-and-error-taxonomy.md` |
| Tenant ids and code flow | `knowledge/mtn-tenant-identifiers-and-code-flow.md` |
| Athena join keys when bridging from Lightstep | `knowledge/mtn-sa-athena-bridge-keys-and-gotchas.md` |
| Saved Lightstep CSV exports (ctap-smvod) | `investigations/ctap-smvod/docs/lightstep-drm-exports.md` |
| Sample spans, household/device field naming | `investigations/mtn-sa-span-attribute-audit/docs/` |

## mDRM EU to US hop

The EU and US projects are separate Lightstep projects reached through separate MCP tool sets (`lightstep-eu_*` for `mcs-go-prod-iye9omdf-eu`, `lightstep-us_*` for `mcs-mdrm-production`). Nothing
joins them except the flow correlation id, which you copy across by hand. Full detail: `knowledge/mtn-sa-mdrm-session-to-device-tracing.md` and
`investigations/ctap-smvod/docs/lightstep-drm-exports.md`. This recipe is from those docs and has not been re-verified live.

1. Resolve the tenant first (`scripts/resolve_tenant.py`); apply the returned filter on the shared EU project. The mDRM tenant is the internal `qfrtzlcj`, not the GO tenant `iye9omdf`.
2. EU `query_spans`: `service == "go-mdrmfe" && drmAuthToken.sessionId == "<abr-vod-...>"`. Read `fcid` (lowercase), `householdId`, `deviceId`, `brRef` and the user agent from the result.
3. US `query_spans`: `fcId == "<fcid from step 2>"`, with a tight time window. This returns the whole license chain (`mdrm-rate-limit` to `authorization-token-service` to `session-state-enforcer` to
   license generation, plus the CDM spans).
4. Tag case differs: `fcid` on EU `go-mdrmfe`, `FCID` on `ctap`/`session-guard`, `fcId` on every US service. A wrong-case filter returns empty without an error.
5. Do not pivot on `sessionId` or `drmAuthToken.jti` on the US side (not indexed), and do not rely on `get_stored_trace` (most spans 404 from sampling).
6. A missing US row is not proof of failure: sampling can drop rows (13 ZA mdrmfe `201` rows had no LRM row). A failure usually shows as EU `go-mdrmfe` 403 with a US LRM 400 on the same `fcId`.

## Pitfalls that recur

- **Tool/syntax split:** the `spans count | delta | ...` pipeline works only in `query_timeseries`; `query_spans` takes a plain `uql_filter`. Use RFC3339 timestamps. `get_stored_trace` needs hex ids,
  and stored traces expire after about 7 days. Treat `list_attributes` as unreliable.
- **Casing and key names differ per service:** `ctap` uses `sessionInfo.deviceId`, most others `deviceId`, `session-guard` uses snake_case `device_id` and filters on `service.name`. OR the variants or
  you silently drop a service's spans.
- **`span.kind`:** `session-guard` is `internal`; filtering `server` returns nothing. Span duration on `session-guard` is meaningless; use `http.request_time` / `http.upstream_response_time`.
- **FCID** is a direct tag on `ctap`/`sm-linear`/`sm-tstv`/`channellineup`, but only inside a log string on `sm-vod`/`households-*`.
- **Do not segment by `deviceType`** (reports `PC` for Android); use `http.user_agent`.
- **A loose OR filter can return another household's or tenant's spans.** Verify `householdId` / `sessionInfo.householdId` on a returned span before trusting it.
- **Ticket-facing content ids do not match CTAP-internal ones** (`<uuid>~WLDP_WLDP<digits>`); resolve the real id from a trace first.
- **`query_timeseries` can under-sample `ctap`** versus `query_spans` or a UI CSV export; cross-check when `ctap` looks missing.
- **Ignore** `Kinesis.PutRecords` 400s (analytics pipeline noise, not a playback failure).
- **Latency:** use `spans latency` with `| point percentile(...)`; server-side span time is often far below client-observed time, so compare against the HAR or pull the trace by FCID.

## After the query

- If you derive a new reusable query, add it per `docs/guides/query-catalog.md`; if you find a new tag or casing quirk, add it to the span-attributes knowledge doc.
- In the session's final summary, name which of the docs above you consulted. `session-close` checks for this.
