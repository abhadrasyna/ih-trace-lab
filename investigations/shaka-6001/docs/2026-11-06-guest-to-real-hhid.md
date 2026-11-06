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

