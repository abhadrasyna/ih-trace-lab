# Usage tracking — sm-vod SetupSession per roster device (live gap-fill)

- Purpose: live (`--live-lightstep`) counterpart of the daily `smvod` export, limited to the tracked `(householdId, deviceId)` pairs. One series per `sessionId` carries the SetupSession request count
  and the `lightstep.trace_id`. There is no `http.status_code` column, matching the local export.
- Tool: `query_timeseries`
- Parameters: `{{pairs_filter}}` is built by `src/pipelines/usage_tracking/lightstep_source.py` from the roster as `(householdId == "<hhid>" && deviceId == "<device>") || ...`, always keeping the two
  together; `{{tenant_filter}}` comes from `scripts/lib/lightstep_export_kinds.py` `resolve_target("smvod", tenant)` (empty unless the tenant shares a project, then `&& busUnitId == "<go_id>"`). The
  window is one UTC day, sliced by `scripts/lib/lightstep_api.py`.
- Registry: tenant project and region come from `config/tenants.yaml` through `resolve_target`.
- Source: derived from `lightstep-export-smvod`.

```
spans count | delta
| filter (service == "sm-linear" || service == "sm-vod")
    && session.api == "SetupSession" && span.kind == "server"{{tenant_filter}}
    && ({{pairs_filter}})
| group_by ["householdId", "deviceId", "sessionId", "lightstep.trace_id"], sum
```
