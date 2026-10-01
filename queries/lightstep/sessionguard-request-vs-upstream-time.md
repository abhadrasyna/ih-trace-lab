# session-guard Request vs. Upstream Time (by device)

- Purpose: `session-guard`'s span duration is meaningless (~1-2ms, see `knowledge/lightstep-span-attributes-by-service.md`) — the real timing lives in its
  `http.request_time`/`http.upstream_response_time` string tags. This query lists every session-guard-observed request for a device with both values side by side, so `request_time -
  upstream_response_time` can be computed per request (session-guard's own overhead) and compared against the CTAP server-span duration and the HAR client round-trip time for the same `FCID` — the
  three-way comparison is what proves whether a delay is upstream of session-guard (network/CDN) or inside it.
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/session-guard-request-vs-upstream.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `session-guard Request vs. Upstream Time (by device)`

```
spans count
| delta
| filter service.name == "session-guard"
    && device_id == "{{device_id}}"
| group_by ["http.route", "http.status_code", "http.request_time", "http.upstream_response_time", "FCID"], sum
```
