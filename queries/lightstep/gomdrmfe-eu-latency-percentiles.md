# go-mdrmfe EU Latency Percentiles (by device/content) — established during issue 7233017, 14 Aug 2026

- Purpose: check DRM/Widevine license backend health for a device — `go-mdrmfe` is the EU proxy in front of the actual US mDRM license generation (see `investigations/instructions/drm-cross-region-
  investigation.md`). Server-side span duration here can be **dramatically lower** than the HAR-observed client wait (confirmed: up to 50x gap, 40ms server-side vs. 1959ms client-observed) — a low
  `go-mdrmfe` latency here, combined with a much higher HAR client-observed wait for the same content/session, is strong evidence the delay is network transit to/from the edge, not the DRM backend.
- Tool: `query_timeseries`
- Save exports as: `investigations/data/{{applause_id}}/lightstep/mdrmfe-eu-latency-percentiles-by-content.csv`
- Source file: `/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md`
- Source section: `go-mdrmfe EU Latency Percentiles (by device/content) — established during issue 7233017, 14 Aug 2026`

```
spans latency
| delta
| filter service == "go-mdrmfe"
    && (deviceId == "{{device_id}}" || request.deviceId == "{{device_id}}")
| group_by ["request.contentId", "http.status_code"], sum
| point percentile(value, 50.0), percentile(value, 95.0), percentile(value, 99.0)
```
