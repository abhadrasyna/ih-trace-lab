# 3016 DRM device link (ctap-smvod) — prompt

> Link each 3016 (and 3014/3015) player error to the household, device and CDM details from the mDRM Lightstep exports, so the "Action for TCS" device pattern analysis can run locally.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Chrome's reduced user agent hides the Android model (about 90% of the Video decode error events show "K"), and the triage table's action for TCS is to map affected households to real devices and see
whether those devices can play at all. The answer lives in mDRM: the EU `go-mdrmfe` span carries the session, household and device; the US license generator spans carry the CDM make, model, platform
and security level. The two projects share no trace, but share the flow correlation id (`fcid` in EU, `fcId` in US). A verified example is in `investigations/ctap-smvod/docs/lightstep-drm-exports.md`.

The exports are saved by hand from two Lightstep notebooks (created 2026-10-24): `MTN SA 3016 – mdrmfe license by session` in `mcs-go-prod-iye9omdf-eu` and `MTN SA 3016 – mDRM license details by fcId`
in `mcs-mdrm-production`. Saving steps, file names and the join are documented in that guide; this story turns the saved CSVs into columns on the sub-category events CSV.

## Scope guard

- **In bounds:** `investigations/ctap-smvod/scripts/`, `tests/`, `docs/`, `data/lightstep/ZA/` (read only), `output/<OPCO>/subcategory_3016/`, plus root `SCRIPTS.md` and `CONTEXT.md` entries.
- **Out of bounds:** `src/`, other investigations, any live Lightstep/Athena call from code (inputs are saved CSVs), CDN or segment-corruption checks, Zambia and Ghana until their mDRM tenant ids are
  known.
- Depends on the events CSV from `ctap-smvod-3016-subcategory-report` (SUB-2 and SUB-4). Do not start DRM-3 before those are done.

## Session-start load hints

- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — file names, attribute names, the join and the verified example.
- `docs/plan/ctap-smvod-3016-subcategory-report/stories.md` — the events CSV columns this story extends.
- `investigations/ctap-smvod/scripts/merge_ctap_smvod_csv.py` — how existing Lightstep UI exports are read (BOM, quoted columns, `sum` count column).

## Task overview

- **DRM-1** — readers for the saved CSVs: mdrmfe, Widevine, PlayReady, FairPlay (parse the `FP_SPC_contents` JSON), LRM.
- **DRM-2** — join builder: session → `fcid` → CDM, with explicit "no license request" and "no CDM row" outcomes.
- **DRM-3** — add the DRM columns to the events CSV and a per-device-model summary CSV.
- **DRM-4** — first real run on ZA 2026-10-22, usage doc, `SCRIPTS.md` and `CONTEXT.md`.

## Definition of done

For a ZA day with all five exports saved, the events CSV gains `household_id`, `device_id`, `fcid`, `drm_type`, `br_ref`, `cdm_make`, `cdm_model`, `platform`, `security_level`, `license_status` and
`drm_join`; a per-device-model summary says which devices played; tests are green and offline; the usage doc and registries are updated.

## Perspectives not covered

- Only ZA (`qfrtzlcj`) is wired; other tenants need their own mDRM tenant id and export folder.
- The join depends on `fcid` being set on the `go-mdrmfe` span; sessions without a license request have no CDM data by definition.
- PlayReady attribute names are not confirmed on a live span (very low volume).
