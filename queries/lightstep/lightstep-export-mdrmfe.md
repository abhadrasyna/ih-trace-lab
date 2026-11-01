# Lightstep export — go-mdrmfe license by session

- Purpose: daily `mdrmfe` export. `{{tenant_filter}}` is always `&& request.tenant == "<go_id>"` (the GO tenant id from `config/tenants.yaml`, not parsed from the project name), even on a dedicated
  project; `{{tenant_group_by}}` is always empty.
- Tool: `query_timeseries` (`POST <base>/<org>/projects/<project>/telemetry/query_timeseries`)
- Parameters: `{{tenant_filter}}` and `{{tenant_group_by}}` are built per tenant by `scripts/lib/lightstep_export_kinds.py`; `{{oldest}}` and `{{youngest}}` are the request window, one UTC day
  `<date>T00:00:00Z` to `<date>T23:59:59Z`, sliced by the client.
- Save exports as: `investigations/ctap-smvod/data/lightstep/{{tenant_code}}/{{date}}_mdrmfe.csv`
- Registry: `scripts/lib/lightstep_export_kinds.py` (kind `mdrmfe`, tenant system `lightstep_go`)
- Source: `docs/plan/lightstep-daily-export-automation/stories.md` "Known queries" (proven in LX-1)

```
spans count | delta
| filter service == "go-mdrmfe" && span.kind == "server"{{tenant_filter}}
| group_by ["drmAuthToken.sessionId", "fcid", "drmAuthToken.householdId", "drmAuthToken.deviceId", "drmAuthToken.deviceType", "drmAuthToken.drmType", "drmAuthToken.brRef",
  "request.contentId", "http.status_code", "http.user_agent", "http.client_ip"{{tenant_group_by}}], sum
```
