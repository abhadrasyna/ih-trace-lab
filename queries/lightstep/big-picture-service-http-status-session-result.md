# Big Picture — Service × HTTP Status × Session Result

- Purpose: one query to get a cross-service overview of everything a device touched in a time window, broken down by service, HTTP outcome, and (where available) the `session.result` pass/fail signal
  — a starting point before drilling into any single service/trace.
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/big-picture-service-status-result.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `Big Picture — Service × HTTP Status × Session Result`

```
spans count | delta
| filter (deviceId == "{{device_id}}" || sessionInfo.deviceId == "{{device_id}}")
| group_by ["service", "http.status_code", "session.result"], sum
```
