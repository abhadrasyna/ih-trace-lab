# mDRM analysis and DRM session funnel (ctap-smvod) — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> add one line to your backlog/session-log file.

All code lives inside `investigations/ctap-smvod/`. Scripts are thin `argparse` CLIs over pure functions in `scripts/lib/`; no hidden file or network I/O in the logic functions; a crash beats a
silently wrong result. Input file and attribute names are defined in `investigations/ctap-smvod/docs/lightstep-drm-exports.md`. Reuse `scripts/lib/drm_exports.py`; extend it only if a needed column is
not exposed.

---

## MDRM-1 — Funnel logic

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel.py` — pure functions, no file or network I/O.
- `investigations/ctap-smvod/tests/test_drm_funnel.py`.

**What to implement:**
1. Session universe: distinct `sessionId` from the CTAP/SMVOD merge (`setupsession_with_outcome`), plus mDRM sessions not in it, each tagged `source` = `merge` or `drm_only`. Tag `kind` = `vod` or
   `linear` from the `abr-vod-` / `abr-linear-` prefix; anything else is `other`. Empty `sessionId` never counts.
2. DRM bucket per session from mdrmfe `drmAuthToken.drmType`: `widevine`, `fairplay`, `playready`, or `none` (no mdrmfe row). A session with several types is `mixed` and counted once.
3. License outcome per session: success (every mdrmfe request `201` and the joined LRM `200`), failed (no success), retry_then_success (a failure followed by a success; file order stands in for time),
   or `no_request`. Use `fcid` to join mdrmfe to LRM.
4. Downstream error per session: first error code from the flat error file (3014/3015/3016, 1xxx, 6xxx, other) or `none`, using the session outcome columns where present.
5. Return one row per (opco, date, source, kind, drm_bucket, license_outcome, error_group) with a `sessions` count, plus stage totals for the funnel summary.

**Tests (no network, no real external services):**
- `test_every_session_in_exactly_one_bucket_and_outcome` — counts sum to the session total.
- `test_drm_only_sessions_are_counted_and_tagged`.
- `test_retry_then_success_and_mixed_drm_type`.
- `test_empty_session_id_is_ignored`.

**Commit:** `feat(ctap-smvod): add DRM session funnel logic`

---

## MDRM-2 — Funnel CLI

**Files to change / create:**
- `investigations/ctap-smvod/scripts/analyze_drm_funnel.py` — `argparse`: `--opco`, `--date` (ISO), `--base`, `--drm-dir`; writes `output/<OPCO>/<date>_drm_funnel.csv` and `<date>_drm_funnel.md`.
- `investigations/ctap-smvod/tests/test_analyze_drm_funnel.py`.

**What to implement:**
1. Read the merge file, the flat error file (optional, empty if absent) and the mDRM exports; call `drm_funnel`; write the CSV and a short markdown summary (stage counts, DRM split, outcome split per
   DRM type, errors per outcome, `drm_only` count called out).
2. Missing mDRM exports for the date raise with the file name; missing merge file raises.
3. Run it for 2026-10-23 on ZA, GH and ZM and check the stage counts reconcile to the unique-session count.

**Tests (no network, no real external services):**
- `test_writes_csv_and_markdown_for_sample_inputs`.
- `test_missing_mdrm_export_raises_with_file_name`.

**Commit:** `feat(ctap-smvod): add DRM funnel report CLI`

---

## MDRM-3 — License-chain quality

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_quality.py` and `scripts/analyze_mdrm_quality.py`; `investigations/ctap-smvod/tests/test_drm_quality.py`.

**What to implement:**
1. Status-code counts per export (mdrmfe, LRM, CDM) by DRM type and OpCo.
2. The failing requests (mdrmfe `403`, LRM `400`): device, household, content, user agent, DRM type; check whether the same `fcId` fails at both layers.
3. Requests per session and per household, and retries (several license calls on one session).
4. `fcId` consistency: in mdrmfe but missing from LRM or CDM, and the reverse; `deviceId` mismatch between mdrmfe and LRM.
5. Duplicate `fcId` across numbered ZA parts, and a warning when a whole-day file coexists with parts (`export_paths` reads both without dedup).

**Tests (no network, no real external services):**
- `test_counts_failures_and_joins_by_fcid`.
- `test_flags_duplicate_fcid_across_parts_and_missing_chain_rows`.

**Commit:** `feat(ctap-smvod): add mDRM license-chain quality report`

---

## MDRM-4 — Device and policy analysis

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_devices.py` and `scripts/analyze_mdrm_devices.py`; `investigations/ctap-smvod/tests/test_drm_devices.py`.

**What to implement:**
1. `brRef` distribution per DRM type, and Widevine `SecurityLevel` L1 against L3 with `brRef=LOW` (the policy finding in the guide).
2. FairPlay device type and OS split from `FP_SPC_contents`, with failure rate; PlayReady listed separately.
3. VOD against linear license outcome.
4. Failing devices (make, model, level) and households ranked with a minimum-volume threshold (argument, default 5).
5. `brRef` across the dates that have exports (2026-10-21 to 2026-10-23) to show whether it is constant.

**Tests (no network, no real external services):**
- `test_l1_with_low_br_ref_is_flagged`.
- `test_min_volume_threshold_hides_small_groups`.

**Commit:** `feat(ctap-smvod): add mDRM device and policy report`

---

## MDRM-5 — Pipeline wiring

**Files to change / create:**
- `investigations/ctap-smvod/scripts/run_pipeline.py` — new step after Step 6h, flag `--skip-drm-funnel`; also skipped when no mDRM exports exist for the date.
- `investigations/ctap-smvod/tests/test_run_pipeline.py` — extend; root `SCRIPTS.md`; `CONTEXT.md` "What Exists".

**What to implement:**
1. Add the funnel step with `--drm-dir` forwarded; update the module docstring step list and `--help`.
2. Register each new script in `SCRIPTS.md` (path, purpose, inputs, outputs).

**Tests (no network, no real external services):**
- `test_funnel_step_present_and_skippable`.
- `test_funnel_step_skipped_without_mdrm_exports`.

**Commit:** `feat(ctap-smvod): run DRM funnel from the pipeline`

---

## MDRM-6 — Docs

**Files to change / create:**
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — new "Attributes worth adding" and "2026-10-23 sample findings" sections.

**What to implement:**
1. List, with the reason for each: span timestamp and duration, error or response body for `403`/`400`, `deviceId` on the CDM exports, token claims behind `brRef`, a PlayReady security level.
2. Record the sample findings (constant `brRef=LOW`, the 29 matching failures, DRM mix) once MDRM-2 to MDRM-4 have run.

**Commit:** `docs(ctap-smvod): list extra mDRM attributes and sample findings`
