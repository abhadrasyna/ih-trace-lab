# ZM 6007 — "Test device not allowed" (TECNO KM5), 2026-10-08

## Summary

Engineering reported a Widevine licence request (Shaka error 6007) from a TECNO KM5 in Zambia. The licence server rejected the device because its Widevine record is flagged as a test device
(`deviceStatus: IN_TESTING`, `testDevice: true`). The failure is deterministic, not a network problem.

## Scope

- Tenant: Zambia (`ZM`, `dtunf6yo`).
- Household: `uHcbwAcpF5F-NVFXT-GEYckvIq7sNFIRa4m4F6mGaUc=YYYY`; device `1714f6c4…a329`.
- Window: 2026-10-08 20:14:46Z to 20:17:06Z, 5 sessions, all with `position_not_moved: true`, `is_wv: false`.
- Content: `9d7f4da0-5320-56ef-a5b7-c100869a1172` (VODStreaming, Widevine); app `v2026.09.16.02`, Shaka 4.12.6.
- Source: `output/ZM/error_eventdata_flat/2026-10-08_6007.csv` and `output/ZM/2026-10-08_error_report_1xxx_6xxx.csv`.

## Error chain

| Layer | Value |
|---|---|
| Client | `E86007` "Unable to create a streaming session at this time" |
| Shaka | 6007 `DRM.LICENSE_REQUEST_FAILED` (category 6) |
| Nested Shaka | 1001 `NETWORK.BAD_HTTP_STATUS`, HTTP 403, problem type `device-insufficient-security-level`, title "Not Authorized" |
| MDRM server | HTTP 400, code **6211**, message **"Test device not allowed"** |
| Endpoint | `api-dtunf6yo.go.synamedia.com/mdrmfe/1.0.0/dtunf6yo/license/VODStreaming/widevine/<content_uuid>` |

## Device (from the engineering licence request)

- TECNO KM5, Android 15, Chrome via MediaDrm (`isChromeCDM: false`); Widevine L1, MediaTek mt6768, Trustonic TEE, OEMCrypto v19, CDM 19.0.1, fused, not debug.
- DRM cert serial `2875dce9b375df4692d96593250494ce27c2d92e1d2776102de8c8b123df5f08`; `systemId` 37783.
- Unclassified fields: `modelStatus`, `platform`, `vulnerabilityLevel` UNSPECIFIED, `analogOutputCapabilities` UNKNOWN; `oem_crypto_security_patch_level` is `"0"`.

## Findings

1. Root cause is the Widevine device record flag (`IN_TESTING`/`testDevice`), enforced by MDRM as 6211.
2. The problem type `device-insufficient-security-level` is misleading: the device is L1, and the rejection is about test-device status.
3. The same 403 repeated across 5 sessions, two client IPs (`102.212.183.125`, `41.223.116.251`) and about 2.5 minutes of retries, so a transient network cause is ruled out.
4. The user agent reports Android 10 (`K`, Chrome 131); the licence request reports Android 15. Chrome freezes its user agent, so the user agent is not reliable for OS version.

## Recommended actions

- Ask engineering/Widevine to confirm the cert serial's device status. If it is a real subscriber device, correct the flag or re-provision; if it is a genuine test unit, the rejection is by design.
- Not yet checked: whether other TECNO KM5 units, other 6211 sessions, or other tenants (SA, GH) show the same rejection.
