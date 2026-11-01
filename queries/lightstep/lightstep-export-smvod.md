# Lightstep export — SM-VOD SetupSession (Session Identity)

- Purpose: daily `smvod` export. Also the source of the derived `smvod-ts`: same query at `output-period` 1 s, the first and last non-zero point per `sessionId` become `oldest_micros` and
  `youngest_micros`; `error_flag`, `component_name`, `span_name` and `duration_millis` are empty placeholders (span samples are not reachable through the public API). On a shared project
  `{{tenant_filter}}` adds `&& busUnitId == "<go_id>"` and `{{tenant_group_by}}` adds `, "busUnitId"`.
- Tool: `query_timeseries` (`POST <base>/<org>/projects/<project>/telemetry/query_timeseries`)
- Parameters: `{{tenant_filter}}` and `{{tenant_group_by}}` are built per tenant by `scripts/lib/lightstep_export_kinds.py` (tenant values from `config/tenants.yaml`, never typed by hand);
  `{{oldest}}` and `{{youngest}}` are the request window, one UTC day `<date>T00:00:00Z` to `<date>T23:59:59Z`, sliced by the client.
- Save exports as: `investigations/ctap-smvod/data/lightstep/{{tenant_code}}/{{date}}_smvod.csv` (and `{{date}}_smvod-ts.csv` for the derived kind)
- Registry: `scripts/lib/lightstep_export_kinds.py` (kinds `smvod` and `smvod-ts`, tenant system `lightstep_go`)
- Source: `docs/plan/lightstep-daily-export-automation/stories.md` "Known queries" (proven in LX-1)

```
spans count | delta
| filter (service == "sm-linear" || service == "sm-vod")
    && session.api == "SetupSession" && span.kind == "server"{{tenant_filter}}
| group_by ["householdId", "deviceId", "session.clientIp", "sessionId", "contentId", "externalPackageId", "lightstep.trace_id", "playbackURL"{{tenant_group_by}}], sum
```
