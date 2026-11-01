# Lightstep export — mDRM CDM FairPlay

- Purpose: daily `mdrm-cdm-fairplay` export on the US `mcs-mdrm-production` project. `{{tenant_filter}}` is always `&& "tenantId" == "<mdrm_tenant_id>"` (mDRM-internal id); the `operation` filter is
  the same for every tenant, including GH. `{{tenant_group_by}}` is always empty.
- Tool: `query_timeseries` (`POST <base>/<org>/projects/<project>/telemetry/query_timeseries`)
- Parameters: `{{tenant_filter}}` and `{{tenant_group_by}}` are built per tenant by `scripts/lib/lightstep_export_kinds.py`; `{{oldest}}` and `{{youngest}}` are the request window, one UTC day
  `<date>T00:00:00Z` to `<date>T23:59:59Z`, sliced by the client. Needs the US API token.
- Save exports as: `investigations/ctap-smvod/data/lightstep/{{tenant_code}}/{{date}}_mdrm-cdm-fairplay.csv`
- Registry: `scripts/lib/lightstep_export_kinds.py` (kind `mdrm-cdm-fairplay`, tenant system `lightstep_mdrm`)
- Source: `docs/plan/lightstep-daily-export-automation/stories.md` "Known queries" (proven in LX-1)

```
spans count | delta
| filter ("service" == "fairplay-license-generator") && (operation == "/MDRM/FPLS/:version/GetLicense"){{tenant_filter}}
| group_by ["fcId", "http.status_code", "FP_SPC_contents"{{tenant_group_by}}], sum
```
