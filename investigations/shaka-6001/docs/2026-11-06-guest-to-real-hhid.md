# Guest login to real HHID (ZA, `onetv1.mtn.com_guest_01.har`)

Capture 2026-11-06 ~04:09-04:14 UTC, Chrome/macOS, app `v2026.11.03.02`. Tenant ZA (`iye9omdf`): Lightstep EU `mcs-go-prod-iye9omdf-eu` and `mcs-matisse-production-eu`, Athena `unified_e6auj7k7`. HAR
parsed with `scripts/har_identity_timeline.py` (output in gitignored `output/`).

## Identity before and after login

| Phase | Time (UTC) | clientId (`<deviceId>:<HHID>`) |
|---|---|---|
| Guest | 04:09:54 - 04:12:15 | `a22e1f0b-9b03-4e0b-84d4-b1b65de39deb:GUEST.a22e1f0b-9b03-4e0b-84d4-b1b65de39deb` |
| Logged in | 04:12:16 onward | `b73708d0a69181ba0c8464835c71e3f41d2bc9e8af93af4ddf49fde3899acb37:mSwS-b3J9_Obw-Fn4awoakB9c2rUO4PWJk_yuE2I5oNdz7p_qkla` |

Both the deviceId and the HHID change: the guest deviceId is a random UUID and the HHID is `GUEST.<same uuid>`. After login the deviceId is a 64-hex device hash and the HHID is the real household.

## Evidence

- **HAR**: the guest clientId appears only in Kinesis `PutRecords` (8 records, from 04:09:57). The login is `POST auth.client-identity.synamedia.com/1z5vo5g2/token` at 04:12:15 (JWT `sub` = `sms|...`,
  an SMS login). The real clientId then appears in Kinesis and as `hhid`/`deviceId` on the SSAI manifest request (04:12:44). The CTAP `x-syna-sessionobject` header is opaque (encrypted), so the guest
  HHID is not readable from CTAP calls.
- **Lightstep, ctap (`mcs-go-prod-iye9omdf-eu`)**: guest spans carry `sessionInfo.guestMode=1` with `sessionInfo.householdId` (or `sessionInfo.logHouseholdId` on the shared-catalogue APIs) equal to
  the bare uuid, with no `GUEST.` prefix. Post-login spans (ctap, households-*, sm-vod) carry the real HHID.
- **Lightstep, client identity (`mcs-matisse-production-eu`, service `Client Identity OAuth`)**: no spans for the guest deviceId or `GUEST.` HHID, so guests never go through OAuth. The real device has
  one `client-id-prod-oauth-authorize-end` (flowType `code`, OAuth clientId `00199aba-6faa-4dff-9a96-f41c5d12c80a.5f5961e6-bf6c-4c51-937e-5a75e6384607`, householdId = real HHID) and the token
  exchange.
- **Athena (`e6auj7k7_ccl_debug_events`, `device_data`)**: guest clientId has 4 events (`APP_DISCOVERY` x2, `ACTION_SCREEN_CHANGE`, `APP_STATE_CHANGE`) from 04:09:54 to 04:09:56. The real clientId's
  first event is `APP_DISCOVERY` at 04:12:16, then `ACTION_LOGON` (`LOGON_SUCCESS`, `profileid` = HHID + `_0`) at 04:12:24. `device_data` lists only the real clientId, with `guest_mode=false`.

## Takeaways

- The guest-to-real mapping is not stored server-side: there is no event with both ids. Correlate by time and device attributes (same browser UA, app version, ZA), or by the HAR as done here.
- The telemetry clientId is a new identity, not an update of the guest one, so guest and logged-in sessions are separate in Athena.
- Guest ids in Lightstep ctap have no `GUEST.` prefix, while Athena clientIds do. Strip or add the prefix when joining.
- Not found: the guest's own `x-syna-sessionobject` / `clientToken` response HHID (not in the HAR as plaintext), and a guest playback (the only playsession in the HAR is post-login).


## Can guest ids be mapped to the real deviceId/HHID?

Short answer: there is no deterministic key anywhere, but a time-bounded join on the client IP works for this sample (ZA, `mcs-go-prod-iye9omdf-eu`).

- **Deterministic link: none found.** The login completion span (`client-id-prod-oauth-authorize-end`, `mcs-matisse-production-eu`) carries `sub`, `accountId`, the real `deviceId` and the real
  `householdId`, but no guest id and no client IP. No ctap, households-* or sm-vod span carries both ids. Athena `device_data` and `e6auj7k7_ccl_debug_events` hold the two clientIds as unrelated rows,
  and `ip_data` has no rows for either device.
- **Probabilistic link: `http.client_ip` on ctap spans.** The guest `clientToken` span (04:09:53Z) has `http.client_ip=203.21.7.200`, `sessionInfo.guestMode=true`, and
  `sessionInfo.deviceId`/`householdId` set to the guest uuid. Filtering ctap on that IP for 04:00-04:30Z returns exactly two identities: the guest device (guestMode=1) and the real device
  `b73708d0...` with HHID `mSwS-...` (guestMode=0). The user agent (Chrome 157 / macOS) and app id (`sessionInfo.matisseAppId`) also match.
- **Limits.** `net.peer.ip` on ctap is an internal proxy hop (10.130.x), so use `http.client_ip` only. The IP recurs across days (guest and logged-in traffic every day since 2026-10-30), so it is only
  unique inside a short window, and carrier NAT or shared Wi-Fi would produce several candidate pairs. A pair is credible only when the IP, a window of a few minutes, the same user agent and guestMode
  flipping from 1 to 0 all agree.
- **Not possible without code changes:** a guest HHID to real HHID mapping that holds for every user. It would need the web client to log the guest clientId in the login request or in `ACTION_LOGON`.
