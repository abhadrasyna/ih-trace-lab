# Knowledge: MTN SA / TIM Play DRM Cross-Tenant Trace Analysis

## Read this first when

Consult this before comparing an MTN SA (`iye9omdf`) versus TIM Play / mileto (`iljyxcc3`) VOD DRM or playsession flow, or before assuming CTAP, manifest, and mDRM response shapes are tenant
invariant.

## MTN SA 4032 case: backend-ready `laUrl`, but no client license request

The MTN SA 4032 comparison used two captures from the same device but different titles:

- **Bilal** — stalled flow
- **Skyf** — successful end-to-end playback

The key finding from the stalled Bilal capture was that `sm-vod` had already returned `drmType: prDrm` and a fully formed PlayReady `laUrl`, but the client never called it. The HAR showed manifest,
Widevine config, and cert traffic, but no `mdrmfe/.../license/...` POST and no playsession teardown. That points to a client-side stall (or a truncated capture) between manifest parsing and PlayReady
challenge generation, not to a backend license-generation failure.

The successful Skyf capture, by contrast, was corroborated end to end through Lightstep by shared `fcId`, proving that the same MTN SA path can complete cleanly when the client reaches the license
acquisition step.

## MTN SA vs TIM Play / mileto comparison

| Aspect | MTN SA (`iye9omdf`) | TIM Play / mileto (`iljyxcc3`) |
| --- | --- | --- |
| CTAP API version path | `/ctap/v1/...` | `/ctap/r1.6.0/...` |
| Content-instance ID family | AXP / UUID-heavy catalogue IDs | CDC / shorter ingest-oriented IDs |
| `laUrl` content segment | Full UUID | Short numeric ingest ID |
| Manifest delivery | Wrapped through Iris SSAI (`vod-dai-ott-.../tenant/sun902py/...`) before the CDN | Direct CDN URL (`mileto.cdnsimba.com.br/...`), no SSAI wrapper |
| `_links` completeness | MTN response carries the fuller linkage set | mileto response is leaner |
| Trick-mode restrictions | Tenant-specific, stricter MTN shaping | Different, simpler restriction shape |
| PlayReady license POST count | Two real requests with distinct FCIDs | One request |

The double-vs-single PlayReady POST count was confirmed, but not explained. The open question remains whether MTN is triggering an intentional dual-license path or a player retry/fallback pattern.

## TIM Play / mileto full-trace chain

The successful TIM Play VOD example traced cleanly across:

```text
ctap → sm-vod → evaluatepolicy / offers-ombo / ipom / gls / households-api / viewinghistory / useraction-agent / vodcontent-get → go-mdrmfe → license.global.multidrm.synamedia.com
```

Key identifiers preserved in the source analysis include:

- tenant / `busUnitId`: `iljyxcc3`
- `householdId`: `iljyxcc3.49041628037`
- `userProfileId`: `iljyxcc3.49041628037_0`
- Device ID: `e169e8117bdcc90b7dbce7a57ca046ac136af85322baba79d8cde9e68b4f147c`
- Playsession ID: `abr-vod-f446e573-6a30-432b-b75d-1a274a127102`
- Playsession-creation FCID: `6A6373E7FE60DF290000F644`
- License-acquisition FCID: `6A6373EEF59DAA2900005F6A`

A crucial methodology point from that trace: these identifiers were visible in the clear only through Lightstep span tags (`sessionInfo.*`, `session.*`, `drmAuthToken.*`). The HAR itself carried only
an opaque, redacted `x-syna-sessionobject` blob.

## TIM Play tenant / configuration reference

The TIM Play configuration analysis preserved the tenant-specific carrier details that are easy to forget:

- CTAP base: `https://api-iljyxcc3.go.synamedia.com/ctap/r1.6.0`
- mDRM frontend base: `https://api-iljyxcc3.go.synamedia.com/mdrmfe/1.0.0/iljyxcc3`
- Content / packager CDN: `https://mileto.cdnsimba.com.br`
- Youbora QoS endpoint: `https://infinity-c37.youboranqs01.com`
- Youbora account/system: `mileto-tim`
- Auth carrier on CTAP calls: `x-syna-sessionobject`, redacted by the HAR capture tool at source rather than by later analysis

## Regional / trace-shape contrast

The two tenants differ materially in DRM trace structure:

- **MTN SA** — `go-mdrmfe` lives in the EU project while the deeper mDRM backend work lands in the US `mcs-mdrm-production` project; trace continuity breaks at that regional boundary and correlation
  depends on business attributes plus time.
- **TIM Play / mileto** — the observed `go-mdrmfe → license.global.multidrm.synamedia.com` hop stayed inside one unbroken trace-propagation domain for the sampled request.

## Stale source index note

All four 2026-07-24 source docs were absent from `github_copilot/investigations/README.md`'s own case-index table at harvest time. That stale-index gap belongs to the read-only source tree; this
harvest records it here without editing the source.

## Source

Source paths: `/Users/abhadra/github_copilot/investigations/docs/20260724-mtn-sa-onetv1-4032-vod-drm-license-flow-analysis.md`,
`/Users/abhadra/github_copilot/investigations/docs/20260724-mtn-vs-timplay-vod-flow-comparison.md`,
`/Users/abhadra/github_copilot/investigations/docs/20260724-timplay-mileto-vod-ctap-sm-vod-mdrm-trace-analysis.md`, and
`/Users/abhadra/github_copilot/investigations/docs/20260724-timplay-tenant-configuration-ltv-playback-analysis.md`. These files are read-only reference, not a shared codebase.
