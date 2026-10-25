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
`python scripts/resolve_tenant.py --system lightstep_mdrm --tenant ZA` before any US query. Ghana (`bb245tf0`) and Zambia (`lcci3mag`) are registered too; Nigeria still needs its own mDRM tenant id.

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

## Attributes worth adding

The 2026-10-23 exports carry no timestamps, no error bodies and no `deviceId` on the CDM side, which limits what `analyze_mdrm_quality.py` and `analyze_mdrm_devices.py` can say. Add these to the
notebook charts the next time they are edited:

| Attribute | Reason |
|---|---|
| Span start timestamp and duration (all five charts) | Enables latency, time-of-day clustering of the `403`/`400` failures and token-to-license delay; row order stands in for time today. |
| Response or error body (`403` on `go-mdrmfe`, `400` on LRM) | The 29 failures have no reason text; the analysis can say who failed, not why. |
| `deviceId` on the CDM exports (Widevine, FairPlay, PlayReady) | The chain check compares `deviceId` between mdrmfe and LRM only; CDM rows can be matched by `fcId` alone. |
| `sessionId` on the LRM and CDM exports | Lets a failing license span be tied to a session without the mdrmfe hop. |
| The token claims behind `brRef` (policy or entitlement claims in `drmAuthToken`) | `brRef=LOW` on every request is a finding; the claim that sets it is the next question. |
| A PlayReady security level (for example `SL2000` / `SL3000`) | PlayReady has none in the export, so an HD-loss check like Widevine's is not possible. |

## 2026-10-23 sample findings

Produced by `analyze_drm_funnel.py`, `analyze_mdrm_quality.py` and `analyze_mdrm_devices.py` for ZA, GH and ZM (the reports live in `output/<OPCO>/`):

- **`brRef` is `LOW` on all 3,343 requests** (ZA 2,614, GH 563, ZM 166), and on every one of the three dates 2026-10-21 to 2026-10-23 for each OpCo. It never varies, so it carries no per-device
  information.
- **HD loss on Widevine:** L1 devices that got `LOW` are 54.3% of Widevine requests in ZA (1,136 of 2,093), 44.1% in GH (199 of 451) and 18.1% in ZM (25 of 138). FairPlay and PlayReady are excluded,
  as they have no L1/L3 split.
- **29 failing requests, all matched across layers:** ZA 15 and GH 14 are an mdrmfe `403` with an LRM `400` on the same `fcId`; ZM has none. In ZA, 12 of the 15 sit on two devices and households with
  6 failures each, and HUAWEI L1 devices failed 12 of 12 requests. In GH one device accounts for 9 of the 14.
- **DRM mix of sessions (ZA):** 2,091 Widevine, 228 FairPlay, 9 PlayReady and 2,024 with no license request, against 4,352 sessions in total.
- **Sessions only in the mDRM exports (`drm_only`):** ZA 8, GH 125 (13.7%) and ZM 14 (9.5%); they are counted in the funnel and marked in the `source` column.
- **`fcId` chain (ZA):** 13 mdrmfe `201` rows have no LRM row and 17 have no CDM row; no `deviceId` differs between mdrmfe and LRM. No `fcId` repeats across the numbered part files.
