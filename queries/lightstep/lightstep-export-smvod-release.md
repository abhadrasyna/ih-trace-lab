# Lightstep export — SM-VOD Release (Session Teardown)

- Purpose: daily `smvod-release` export, the teardown counterpart of `lightstep-export-smvod` (SetupSession). One row per `sessionId` and teardown reason for every `Release` call `sm-vod` served, so a
  session's SetupSession/Release pair can be checked against Athena outcomes (`analyze_ebvs_release_coverage.py`). On a shared project `{{tenant_filter}}` adds `&& busUnitId == "<go_id>"` and
  `{{tenant_group_by}}` adds `, "busUnitId"`; whether Release spans carry `busUnitId` on the shared Ghana/Zambia project is not yet verified (only ZA, a dedicated project, has been checked).
- Tool: `query_timeseries` (`POST <base>/<org>/projects/<project>/telemetry/query_timeseries`)
- Parameters: `{{tenant_filter}}` and `{{tenant_group_by}}` are built per tenant by `scripts/lib/lightstep_export_kinds.py`; `{{oldest}}` and `{{youngest}}` are the request window, one UTC day
  `<date>T00:00:00Z` to `<date>T23:59:59Z`, sliced by the client. A session that starts late in the day releases after midnight UTC, so its Release is in the next day's file.
- Save exports as: `investigations/ctap-smvod/data/lightstep/{{tenant_code}}/{{date}}_smvod-release.csv`
- Registry: `scripts/lib/lightstep_export_kinds.py` (kind `smvod-release`, tenant system `lightstep_go`)
- Source: ad-hoc Lightstep probe on 2026-11-01 17:00-18:00Z (ZA): `session.api == "Release"` was served only by `sm-vod`, `span.kind == "server"`, HTTP 204.

```
spans count | delta
| filter service == "sm-vod" && session.api == "Release" && span.kind == "server"{{tenant_filter}}
| group_by ["sessionId", "http.status_code", "externalTeardownReason"{{tenant_group_by}}], sum
```
