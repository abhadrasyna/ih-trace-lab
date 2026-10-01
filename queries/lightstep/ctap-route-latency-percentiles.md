# CTAP Route Latency Percentiles (by device)

- Purpose: —
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/ctap-route-latency-percentiles.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `CTAP Route Latency Percentiles (by device)`

```
spans latency
| delta
| filter service == "ctap"
    && sessionInfo.deviceId == "{{device_id}}"
    && span.kind == "server"
| group_by ["http.route", "request.api", "http.status_code"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```
