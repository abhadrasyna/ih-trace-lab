# Lightstep export — CTAP CreatePlaySession (User-Agent)

- Purpose: daily `ctap` export, CTAP playsession spans by user agent and trace id. On a shared project `{{tenant_filter}}` adds `&& sessionInfo.busUnitId == "<go_id>"` and `{{tenant_group_by}}` adds
  `, "sessionInfo.busUnitId"`; on a dedicated project both are empty.
- Tool: `query_timeseries` (`POST <base>/<org>/projects/<project>/telemetry/query_timeseries`)
- Parameters: `{{tenant_filter}}` and `{{tenant_group_by}}` are built per tenant by `scripts/lib/lightstep_export_kinds.py` (tenant values from `config/tenants.yaml`, never typed by hand);
  `{{oldest}}` and `{{youngest}}` are the request window, one UTC day `<date>T00:00:00Z` to `<date>T23:59:59Z`, sliced by the client.
- Save exports as: `investigations/ctap-smvod/data/lightstep/{{tenant_code}}/{{date}}_ctap.csv`
- Registry: `scripts/lib/lightstep_export_kinds.py` (kind `ctap`, tenant system `lightstep_go`)
- Source: `docs/plan/lightstep-daily-export-automation/stories.md` "Known queries" (proven in LX-1)

```
spans count | delta
| filter http.route == "/ctap/:uxApiVersion/devices/me/playsessions"{{tenant_filter}}
| group_by ["http.user_agent", "lightstep.trace_id"{{tenant_group_by}}], sum
```
