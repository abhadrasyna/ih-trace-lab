# Lightstep DRM exports — how to save the CSVs

Links a 3016 player error to the household, device and CDM (make, model, security level) that tried to play, using two Lightstep notebooks. Both are one table per chart, exported to CSV by hand from
the Lightstep UI (the MCP cannot be scripted, and its long outputs truncate).

## The two notebooks

| Project | Notebook | Chart | Save as |
|---|---|---|---|
| `mcs-go-prod-iye9omdf-eu` (EU) | `MTN SA 3016 – mdrmfe license by session` | go-mdrmfe license by session | `data/lightstep/ZA/<date>_mdrmfe.csv` |
| `mcs-mdrm-production` (US) | `MTN SA 3016 – mDRM license details by fcId` | `CDM – Widevine` | `data/lightstep/ZA/<date>_mdrm-cdm-widevine.csv` |
| `mcs-mdrm-production` (US) | same notebook | `CDM – FairPlay` | `data/lightstep/ZA/<date>_mdrm-cdm-fairplay.csv` |
| `mcs-mdrm-production` (US) | same notebook | `CDM – PlayReady` | `data/lightstep/ZA/<date>_mdrm-cdm-playready.csv` |
| `mcs-mdrm-production` (US) | same notebook | `License chain status – LRM` | `data/lightstep/ZA/<date>_mdrm-lrm.csv` |

The EU chart title is blank in the notebook; give it the name above when you next edit it. The EU query also filters `span.kind == "server"` so each license request counts once.

## Saving one day

1. Open the notebook in the Lightstep UI (links: `https://app.lightstep.com/mcs-mdrm-production/notebooks/N866YJ6f` and the EU project's notebook `KR1Nn4v6`).
2. Set the time range to the UTC calendar day (00:00–24:00 UTC), the same convention as the other `data/lightstep/ZA/` exports.
3. For each chart, use the chart's export (CSV) action and save it to `investigations/ctap-smvod/data/lightstep/ZA/` with the name in the table. Do not rename columns.
4. If a chart hits the UI row limit, export in hourly slices and name them `<date>_01_<kind>.csv`, `<date>_02_<kind>.csv`, the way the existing `_01`/`_02` ctap and smvod files are split.

Only the ZA tenant is covered. The US queries are filtered to the mDRM-internal tenant `qfrtzlcj` (MTN SA), which is not the GO tenant `iye9omdf`. It is registered in `config/tenants.yaml`; run
`python scripts/resolve_tenant.py --system lightstep_mdrm --tenant ZA` before any US query. Ghana (`bb245tf0`) is registered too; Zambia and Nigeria still need their own mDRM tenant ids.

## Attribute names (case matters)

| Where | Attribute | Notes |
|---|---|---|
| EU `go-mdrmfe` | `fcid` (lowercase) | `FCID` uppercase is blank on this service. |
| US all services | `fcId` | Same value as the EU `fcid`. |
| EU `go-mdrmfe` | `drmAuthToken.sessionId` | Equals the `sessionId` (`abr-vod-…`) in setupsession and in the 3016 events. |
| EU and US | `drmAuthToken.deviceId` / `deviceId` | Must match across the two projects. |
| US Widevine | `drmInfo.DeviceType`, `Make`, `Model`, `Platform`, `SecurityLevel` | |
| US PlayReady | `drmInfo.deviceType`, `manufacturerName`, `modelName` | Names taken from the notebook; low volume (about 21 a day), not confirmed on a live span. |
| US FairPlay | `FP_SPC_contents` | One JSON string: `DeviceInfo` (for example `Type:iPhone,OS:26.6.0`), `DeviceIdentity`, `SecurityLevel`. There is no `drmInfo.*`. |

## The join

```
3016 event.sessionId
  -> <date>_mdrmfe.csv        drmAuthToken.sessionId  -> fcid, householdId, deviceId, brRef, user agent
  -> <date>_mdrm-cdm-*.csv    fcId == fcid            -> CDM make / model / platform / security level
  -> <date>_mdrm-lrm.csv      fcId == fcid            -> per-request status and deviceId cross-check
```

- A session with no `mdrmfe` row made no license request.
- An `mdrmfe` row with no CDM row failed before the license generator, or the request is on a DRM scheme not exported.
- `brRef=LOW` is a Widevine L3 policy (SD only); `HIGH` is L1. A device can report `SecurityLevel=L1` while the token says `LOW`, which is a policy finding, not a data error.
- Each license generator span carries `fcId`, so no stored trace is needed. `get_stored_trace` returns 404 for most spans (sampling), so do not rely on it.

## Worked example (verified 2026-10-24)

`fcid 6ADCA78ABAA1B5290003C530` → `sessionId abr-vod-21f5d080-e427-453f-aa09-edbbabd92a4e`, `deviceId 684b86fc…ac32b`, user agent Android "K" with Samsung Browser, `brRef=LOW`, status 201 → US
Widevine span: Samsung a05s, `PHONE`, `ANDROID`, `L1`, status 200. The reduced user agent hid the model; the CDM data resolved it.
