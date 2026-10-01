# Playsessions Call Latency Isolation

- Purpose: —
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/playsessions-latency-by-operation.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `Playsessions Call Latency Isolation`

```
spans latency
| delta
| filter service == "ctap"
    && sessionInfo.deviceId == "{{device_id}}"
    && http.route == "/ctap/:uxApiVersion/devices/me/playsessions"
| group_by ["request.api"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```
