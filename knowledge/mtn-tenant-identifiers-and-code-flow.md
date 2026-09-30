# Knowledge: MTN Tenant Identifiers and Code Flow

## Read this first when

Consult this before looking up an MTN SA tenant/auth/ad-tenant ID, before tracing a Widevine or PlayReady license acquisition end to end, or before assuming household/device/profile identifiers are
all available from HAR alone.

## Analysis-session quick reference

The source HAR session covered **140 requests** with **0 HTTP errors** and **3 aborted** requests. Its quick-reference identifiers were:

| Identifier | Value |
| --- | --- |
| Primary tenant | `iye9omdf` |
| Auth tenant / client-identity project | `1z5vo5g2` |
| Iris ad tenant | `sun902py` |
| Household ID | `b7RAnRFPpzh1G8SIZWZCxA5ZBhxbb-JNPorWZW1v_ITZUu4aBswL` |
| Device ID | `114cdd2725e34d0cd43ee8f370f50249025101db6b2edf4ff32c6d107dba47be` |
| Play-session ID | carried in the captured playback flow (`abr-vod-*` in the playsession path) |
| Kinesis stream | `datastream-e6auj7k7` |
| AWS Cognito identity | `eu-central-1:1ffae455-691c-c0f9-bc3a-17235ce82e3c` |
| Country (Kinesis) | `ZA` |
| Country (CTAP/session context) | `USA` |

That Kinesis-versus-CTAP country mismatch was explicitly confirmed in the source notes and is part of the reusable reference, not an assumed typo.

## Static reference findings from the HAR session

### Kinesis stream

- Stream: `datastream-e6auj7k7`
- 8 batches, 51 events decoded
- Duplicate-batch bug confirmed
- Two-step Cognito credential flow observed: identity acquisition, then temporary AWS credentials used to sign the Kinesis `PutRecords` calls

### Cookies

Three cookies were called out as structurally important:

- `cmty` (JSON)
- `WsbSession` (JWT / HS256)
- `subs` (MessagePack + HMAC)

All three were flagged as missing `HttpOnly` and `Secure` in the captured flow.

### Manifests / metadata

Four manifest/config artefacts were identified in the session:

- CTAP `/resources/initial`
- Iris `discovery.json`
- Iris `logging.json`
- DASH MPD

### DRM / token findings

- Dual-DRM behaviour was confirmed: Widevine plus PlayReady.
- `brRef: LOW` explains the observed SD-only cap.
- Five token families were decoded in the source analysis, including the long-lived refresh token, the tightly scoped DRM-license JWT, Cognito-derived AWS credentials, and the request signatures used
  for Kinesis.
- The refresh token was explicitly flagged as the highest-risk credential in the HAR because of its long lifetime.

## Code-flow reference

The companion `_code_flow.md` file is structured as a debugging cookbook. This harvested summary keeps the same lookup shape while collapsing the long narrative.

### 1. mDRM code flow — Widevine license acquisition

The license path is a two-leg flow:

1. the client-side request lands on EU `go-mdrmfe`;
2. `go-mdrmfe` issues the backend license-generation call to the US-side mDRM services.

The source explicitly notes that the outbound `traceparent` header is **not forwarded** on the EU → US call, so the US mDRM creates a fresh trace. Correlation therefore depends on business attributes
such as `drmAuthToken.jti`, `contentId`, `deviceId`, and a tight timestamp window rather than a shared `trace_id`.

### 2. Client Identity code flow — device registration and token acquisition

The source preserves the full client-identity path from household and device registration through OAuth token exchange. Its key reusable value is the identity lifecycle order:

- device-registration and household-registration calls establish the stable hardware/account identifiers;
- OAuth steps surface `clientId` and token-level identifiers;
- different IDs become visible at different layers, so HAR-only debugging can miss values that later appear in Lightstep span tags.

### 2.13 Identity lifecycle — when each ID becomes available

This is the most reusable section from `_code_flow.md`: it explicitly records **when** each identifier first becomes visible. Household, device, profile, playsession, and DRM-token identifiers do not
all arrive at the same step. Some become visible only in Lightstep span attributes rather than in raw HAR headers.

### 3. GO platform code flow — CTAP, session-guard, Households, and EU DRM proxy

The platform-side chain documented there is the reference flow for MTN SA debugging:

```text
session-guard → ctap → households / playsession / sm-vod / go-mdrmfe
```

The companion catalogue also records which Lightstep project and service family each hop belongs to, so a debugger knows whether to stay in GO/IH, switch to Matisse/client identity, or jump to US
mDRM.

### 3.1 Lightstep project and service catalogue

`_code_flow.md` lists the project/service mapping needed for debugging pivots:

- GO/IH platform services under the MTN SA production project
- client-identity / Matisse services under the auth project
- US mDRM services under `mcs-mdrm-production`

### 3.2 Session-guard

The source treats `session-guard` as the edge ingress proxy in front of CTAP and documents it as its own debugging hop, not just a footnote. That matters because FCID can cross this boundary even when
trace continuity does not.

### 3.8 `go-mdrmfe` and the EU→US split

The GO platform section also records the `go-mdrmfe` pivot explicitly: the EU trace and US trace are separate, and the outbound POST to `license.global.multidrm.synamedia.com` starts only a few
milliseconds into the EU trace. That section is the worked example for the broader DRM cross-region method.

### 3.11 Lightstep debugging pivots

The source ends with reusable debugging pivots: household-scoped CTAP tracing, device-scoped tracing, and focused `go-mdrmfe` lookups for DRM analysis.

### Common failure modes

The cookbook also preserves a list of common failure modes spanning:

- missing or broken trace continuity across the EU→US DRM boundary;
- client-side failures before the license request is ever sent;
- mismatched expectations about which layer exposes a given identifier.

## Forward note for `tenant-registry`

This repository's `docs/plan/tenant-registry/` story is not implemented yet. When that resolver work begins, it should consult this file instead of re-deriving MTN tenant-ID facts from scratch.

## Source

Source paths: `/Users/abhadra/github_copilot/investigations/docs/ITZUu4aBswL.md` and `/Users/abhadra/github_copilot/investigations/docs/ITZUu4aBswL_code_flow.md`. These files are read-only reference,
not a shared codebase.
