# Knowledge: MTN SA mDRM session-to-device tracing (go-mdrmfe → US mDRM)

## Read this first when

Consult this before mapping a player error (3016, 3014/3015, 4xxx) or a household to the real device and CDM that played, or before querying `mcs-mdrm-production` for device details.

## The path

A playback session reaches mDRM in two Lightstep projects that share no trace id:

1. **EU `mcs-go-prod-iye9omdf-eu`, service `go-mdrmfe`** — carries `drmAuthToken.sessionId` (the `abr-vod-…` id used in setupsession and the player error events), `drmAuthToken.householdId`,
   `drmAuthToken.deviceId`, `drmAuthToken.brRef`, `request.contentId`, the raw user agent, and the flow correlation id as lowercase `fcid`.
2. **US `mcs-mdrm-production`** — every service of the same license request carries that id as `fcId`. The chain is `mdrm-rate-limit` → `authorization-token-service` → `session-state-enforcer` →
   `license-request-manager` → `content-key-generator` → `license-generator-proxy` → the DRM license generator (`widevine-license-generator`, `playready`, `fairplay-license-generator`).

The exact join is `sessionId` → `fcid` → `fcId`. The mDRM tenant id is the internal one (`qfrtzlcj` for MTN SA), not the GO tenant `iye9omdf`.

## What each service tells you

- **Device model, make, platform, security level:** the license generator span. Widevine and PlayReady carry `drmInfo.*` (different attribute names); FairPlay carries one JSON attribute
  `FP_SPC_contents` with `DeviceInfo`, `DeviceIdentity` and `SecurityLevel`.
- **Device id:** only on `authorization-token-service`, `session-state-enforcer` and `license-request-manager`; equals EU `drmAuthToken.deviceId`.
- **Did the license issue:** `http.status_code` per US service (200 = issued; the EU `go-mdrmfe` span is 201).
- **Policy vs hardware:** `brRef=LOW` means Widevine L3 policy (SD only); `HIGH` means L1. A hardware-L1 phone can still receive a `LOW` token.

## Why this matters for player errors

Chrome's reduced user agent shows Android model "K", hiding the device. The CDM details resolve it (verified 24 Oct 2026: session `abr-vod-21f5d080-…` showed "K" in the user agent and a Samsung a05s,
L1, in the Widevine span). MTN SA volume over 24 h: Widevine ~2,211, FairPlay ~534, PlayReady ~21 license calls, so FairPlay (iOS) cannot be ignored.

## Gotchas

- **Attribute case differs by service:** `fcid` (EU `go-mdrmfe`), `FCID` (`session-guard`, `ctap`), `fcId` (US). A wrong-case filter or `group_by` silently returns empty.
- **`get_stored_trace` 404s for most spans** (adaptive sampling), by span id or by trace id plus `start_time`. Use `query_timeseries` with `group_by` to read attribute values instead.
- **`list_attributes` is broken** in the MCP wrapper; the tool parameter names are `oldest_time` / `youngest_time` on `query_spans` and `query_timeseries`.
- **`jti` and `sessionId` are not indexed on the US side**; the `drmAuthToken.jti` pivot does not work, `fcId` does.
- **No `drmInfo.*` on FairPlay**, and PlayReady attribute names are taken from a saved notebook, not confirmed on a live span.

## Where it is implemented

- Hand-run guide and saved-export procedure: `investigations/ctap-smvod/docs/lightstep-drm-exports.md` (notebooks `MTN SA 3016 – mdrmfe license by session` and `MTN SA 3016 – mDRM license details by
  fcId`).
- Planned local join into the 3016 events CSV: `docs/plan/ctap-smvod-3016-drm-device-link/`.
- Full MCP rules: `/Users/abhadra/github_copilot/investigations/instructions/lightstep-mcp-tool-notes.md` (rules 14–17) and `drm-cross-region-investigation.md` (Step 2a).
