# sm-vod Session Inventory by Device

- Purpose: enumerate every `sm-vod` streaming session a device touched in a window, with full session/content context and outcome — a per-session inventory to cross-check against HAR-derived session
  IDs (the `sessions` subcommand of `scripts/analyze_har.py`) or to spot which specific sessions/content failed.
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/smvod-sessions-by-content.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `sm-vod Session Inventory by Device`

```
spans count | delta
| filter service == "sm-vod"
    && deviceId == "{{device_id}}"
| group_by ["householdId", "deviceId", "session.clientIp", "sessionId", "http.status_code", "contentId", "externalPackageId", "lightstep.trace_id", "playbackURL"], sum
```
