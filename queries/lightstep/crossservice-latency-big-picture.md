# Cross-Service Latency Big Picture

- Purpose: —
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/big-picture-service-route-latency.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `Cross-Service Latency Big Picture`

```
spans latency
| delta
| filter (deviceId == "{{device_id}}" || sessionInfo.deviceId == "{{device_id}}")
| group_by ["service", "http.route"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```
