# 3016 DRM device link (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> add one line to your backlog/session-log file.

All code lives inside `investigations/ctap-smvod/`. Scripts are thin `argparse` CLIs over pure functions; no hidden file or network I/O in the logic functions; a crash beats a silently wrong result.
Input file names and attribute names are defined in `investigations/ctap-smvod/docs/lightstep-drm-exports.md`.

---

## DRM-1 — CSV readers

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_exports.py` — one reader per file kind, returning typed rows.
- `investigations/ctap-smvod/tests/test_drm_exports.py`.

**What to implement:**
1. Read with `encoding="utf-8-sig"` (the UI export starts with a BOM). Required columns per kind: mdrmfe (`drmAuthToken.sessionId`, `fcid`, `drmAuthToken.householdId`, `drmAuthToken.deviceId`,
   `drmAuthToken.brRef`, `drmAuthToken.drmType`, `http.status_code`), Widevine (`fcId`, `drmInfo.Make`, `drmInfo.Model`, `drmInfo.Platform`, `drmInfo.SecurityLevel`), PlayReady (`fcId`,
   `drmInfo.manufacturerName`, `drmInfo.modelName`), FairPlay (`fcId`, `FP_SPC_contents`), LRM (`fcId`, `deviceId`, `http.status_code`). A missing column raises with the file name.
2. Parse FairPlay `FP_SPC_contents` JSON: `DeviceInfo` (`Type:iPhone,OS:26.6.0`) to device type and OS, and `SecurityLevel`; invalid JSON yields empty fields, not a crash.
3. Hourly slices (`<date>_01_<kind>.csv`) are read together with the day file when both exist.

**Tests:**
- `test_reads_bom_csv_and_requires_columns`.
- `test_fairplay_spc_parsed_to_device_and_security_level`.
- `test_invalid_fairplay_json_gives_empty_fields`.

**Commit:** `feat(ctap-smvod): add mDRM Lightstep export readers`

---

## DRM-2 — Join builder

**Files to change / create:**
- `investigations/ctap-smvod/scripts/build_3016_drm_link.py` — `link(events, mdrmfe, cdm, lrm)`.
- `investigations/ctap-smvod/tests/test_build_3016_drm_link.py`.

**What to implement:**
1. `sessionId` to `drmAuthToken.sessionId` gives `fcid`, `household_id`, `device_id`, `br_ref`, `drm_type`. Then `fcid` to `fcId` in the CDM file for that `drm_type` gives make, model, platform and
   security level. LRM gives `license_status` and a `deviceId` cross-check.
2. `drm_join` is exactly one of `joined`, `no_license_request` (no mdrmfe row), `no_cdm_row` (mdrmfe row without a CDM row). Empty `sessionId`, `fcid` or `fcId` never join.
3. A session with several mdrmfe rows (retries) keeps the latest successful one, else the latest.

**Tests:**
- `test_session_joins_to_cdm_via_fcid` (the verified example: Samsung a05s, L1, `brRef=LOW`).
- `test_missing_rows_give_explicit_outcomes`.
- `test_empty_keys_never_join`.

**Commit:** `feat(ctap-smvod): join 3016 events to mDRM device details`

---

## DRM-3 — Events columns and device summary

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_3016_subcategory_report.py` (from the sub-category story) — optional `--drm` flag that adds the columns.
- `investigations/ctap-smvod/scripts/build_3016_drm_device_summary.py` — `summarise(events)`.
- tests for both.

**What to implement:** add `household_id, device_id, fcid, drm_type, br_ref, cdm_make, cdm_model, platform, security_level, license_status, drm_join` to the events CSV without changing its row count.
Write `<date>_subcategory_device_summary.csv` with `opco, subcategory, cdm_make, cdm_model, security_level, events, households, license_ok`.

**Tests:** `test_event_row_count_unchanged_with_drm`, `test_device_summary_counts_distinct_households`.

**Commit:** `feat(ctap-smvod): add DRM device columns and device summary`

---

## DRM-4 — First run and docs

**Files to change / create:**
- `investigations/ctap-smvod/docs/usage.md` — the `--drm` run, inputs and outputs.
- `SCRIPTS.md` (via `python scripts/dev/generate_scripts_registry.py`) and `CONTEXT.md` "What Exists".

**What to implement:** save the five exports for ZA 2026-10-22 as in the guide, run the CLI with `--drm`, and record the join outcome counts and the top device models for the Video decode error
sub-category in the usage doc.

**Tests:** none beyond the earlier tasks; confirm the registry lists the new scripts.

**Commit:** `docs(ctap-smvod): document 3016 DRM device link`
