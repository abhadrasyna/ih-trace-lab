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

## MDRM-2a — Shared stacked-bar chart

**Files to change / create:**
- `src/lib/charts/theme.py` — add an ordered series palette to `ChartTheme` and `DARK` (distinguishable on the dark background; `green` and `red` stay reserved for success and failure).
- `src/lib/charts/stacked_bar.py` — `render_stacked_bar`; `src/lib/charts/__init__.py` exports if the package does.
- `tests/` — tests next to the existing chart tests (find them with the existing `render_bar` tests); `docs/guides/chart-guidelines.md`; root `CONTEXT.md` "What Exists".

**What to implement:**
1. `render_stacked_bar(labels, series, *, title, subtitle="", horizontal=False, colours=None, theme=DARK) -> bytes`, where `series` maps a series name to one value per label. A series colour comes
   from `colours` (a name to theme-token map, for example success green and failure red) or else the palette in order; no hex literal outside `theme.py`.
2. Validate: at least one label and one series, equal lengths, no negative or non-finite values. Raise `ChartError` for bad input and wrap any drawing failure, like `render_bar`.
3. Label segments directly with the value (and share when a total is given); no legend unless there are more segments than can be labelled. Reuse `style_axes`, `new_figure`, `render_png` and
   `chart_font_family()`; no `pyplot`.
4. Update `chart-guidelines.md` with the new function, the palette tokens and the reserved success/failure colours.

**Tests (no network, no real external services):**
- `test_renders_png_bytes_for_vertical_and_horizontal` — output starts with the PNG signature.
- `test_unequal_series_lengths_and_negative_values_raise_chart_error`.
- `test_series_colours_come_from_theme_palette` — the existing guard test for hex literals still passes.

**Commit:** `feat(charts): add stacked bar chart and series palette`

---

## MDRM-2b — Funnel charts

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` — pure series builders plus thin render wrappers; `investigations/ctap-smvod/scripts/analyze_drm_funnel.py` — call them and embed the
  images; `investigations/ctap-smvod/tests/test_drm_funnel_charts.py`.

**What to implement:**
1. Series builders from the MDRM-1 funnel rows (pure, testable): stage counts (sessions, DRM requested, license success, errored), the DRM-type split, and license outcome per DRM type with success in
   green and failure in red, split further by downstream error group (3016 and others).
2. Render three PNGs per OpCo and date with `render_stacked_bar` (and `HeaderCell` stats for totals and `drm_only`), written with `write_chart_png` to
   `output/<OPCO>/charts/<date>_drm_funnel_<name>.png`.
3. Embed them in `<date>_drm_funnel.md` with relative links (`charts/<file>`). A `ChartError` is logged, the link is left out, and the CSV and markdown are still written.

**Tests (no network, no real external services):**
- `test_series_builders_reconcile_to_session_total`.
- `test_chart_error_still_writes_csv_and_markdown_without_image_links`.
- `test_markdown_embeds_relative_chart_links`.

**Commit:** `feat(ctap-smvod): chart the DRM funnel in the markdown summary`

---

## MDRM-2c — Error-code split

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel.py` — add an `error_code` field (first code per session, same rule as `error_group`) to `FunnelRow`; `scripts/analyze_drm_funnel.py` — new markdown
  tables and the CSV column; extend `tests/test_drm_funnel.py` and `tests/test_analyze_drm_funnel.py`.

**What to implement:**
1. Carry the exact first error code (6001, 1003, 3016, E31012 and so on) alongside `error_group`; `none` when the session has no error. The CSV gains an `error_code` column.
2. Markdown "Ended in error by code": one row per code with sessions, share of errored sessions and the license outcome split (success, retry_then_success, failed, no_request) as counts and shares.
3. Replace the loose 3016 sentence with a table: for each of 3014, 3015 and 3016, sessions by license outcome with counts and shares, plus a one-line reading ("most 3016 sessions had a successful
   license").
4. State in the markdown that each session is counted under its first error code only.

**Tests (no network, no real external services):**
- `test_error_code_counts_sum_to_errored_sessions`.
- `test_3016_table_splits_by_license_outcome`.

**Commit:** `feat(ctap-smvod): split funnel errors by code and license outcome`

---

## MDRM-2d — 3014/3015/3016 sub-categories

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel_subcategory.py` — pure join of funnel sessions to the sub-category from `classify_3016_subcategory.py`; `scripts/analyze_drm_funnel.py` — read the
  flat events, merge and position report (as `run_3016_subcategory_report.py` does) and add the section; `tests/test_drm_funnel_subcategory.py`.

**What to implement:**
1. Reuse the existing classifier and `build_events`; do not copy its rules. A missing position report warns and leaves the affected sessions in the classifier's own fallback bucket, as the
   sub-category report does.
2. Markdown "3014/3015/3016 by sub-category": sub-category by license outcome, with counts and shares; sessions without a 3014/3015/3016 error are not included.
3. Reconcile: the sessions listed equal the 3014/3015/3016 sessions in the MDRM-2c table.

**Tests (no network, no real external services):**
- `test_subcategory_by_license_outcome_for_sample_sessions`.
- `test_subcategory_sessions_reconcile_to_3016_table`.

**Commit:** `feat(ctap-smvod): split 3016-family errors by sub-category in the funnel`

---

## MDRM-2e — Pie chart and error-mix charts

**Files to change / create:**
- `src/lib/charts/pie.py` — `render_pie`; `src/lib/charts/__init__.py` exports if the package does; the chart tests next to `render_bar`; `docs/guides/chart-guidelines.md`; root `CONTEXT.md` "What
  Exists".
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` — pure series builders; `scripts/analyze_drm_funnel.py` — render and embed; `tests/test_drm_funnel_charts.py`.

**What to implement:**
1. `render_pie(labels, values, *, title, subtitle="", donut=True, max_slices=6, theme=DARK) -> bytes`: slices beyond `max_slices - 1` merge into `other`; colours come from the MDRM-2a theme palette,
   no hex literal outside `theme.py`; every slice is labelled with value and share. Validate input and raise `ChartError`, wrapping any drawing failure, like `render_bar`; no `pyplot`.
2. Two funnel charts per OpCo and date, written with `write_chart_png` to `output/<OPCO>/charts/<date>_drm_funnel_error_codes.png` and `..._3016_subcategory.png`: errored sessions by code (top 5 plus
   other) and 3014/3015/3016 sessions by sub-category.
3. Embed both in the funnel markdown with relative links. A `ChartError` is logged, the link is left out, and the CSV and markdown are still written.

**Tests (no network, no real external services):**
- `test_render_pie_returns_png_and_merges_small_slices_into_other`.
- `test_invalid_pie_input_raises_chart_error`.
- `test_error_mix_series_reconcile_to_errored_sessions`.

**Commit:** `feat(charts): add pie chart and chart the funnel error mix`

---

## MDRM-3 — License-chain quality

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_quality.py` and `scripts/analyze_mdrm_quality.py`; `investigations/ctap-smvod/tests/test_drm_quality.py`.

**What to implement:**
1. Status-code counts per export (mdrmfe, LRM, CDM) by DRM type and OpCo.
2. The failing requests (mdrmfe `403`, LRM `400`): device, household, content, user agent, DRM type; check whether the same `fcId` fails at both layers, and whether the same device, household or
   session fails more than once (repeat failures).
3. Requests per session and per household, and retries (several license calls on one session).
4. `fcId` consistency: in mdrmfe but missing from LRM or CDM, and the reverse; `deviceId` mismatch between mdrmfe and LRM only (the CDM exports have no `deviceId` or `sessionId`, so a mismatch cannot
   be checked against them).
5. Duplicate `fcId` across numbered ZA parts, and a warning when a whole-day file coexists with parts (`export_paths` reads both without dedup).

**Tests (no network, no real external services):**
- `test_counts_failures_and_joins_by_fcid`.
- `test_flags_duplicate_fcid_across_parts_and_missing_chain_rows`.
- `test_repeat_failures_by_device_household_and_session`.

**Commit:** `feat(ctap-smvod): add mDRM license-chain quality report`

---

## MDRM-4 — Device and policy analysis

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_devices.py` and `scripts/analyze_mdrm_devices.py`; `investigations/ctap-smvod/tests/test_drm_devices.py`.

**What to implement:**
1. `brRef` distribution per DRM type, and Widevine `SecurityLevel` L1 against L3 with `brRef=LOW` (the policy finding in the guide). Size the HD loss: the number and share of Widevine requests and
   sessions that are L1 but got `LOW`.
2. FairPlay device type and OS split from `FP_SPC_contents`, with failure rate; PlayReady listed separately. FairPlay has no L1/L3 split, so `LOW` there is reported as the likely default, not a
   downgrade, and is excluded from the HD-loss count.
3. VOD against linear license outcome.
4. Failing devices (make, model, level), households and `contentId`s ranked by failure count and failure rate with a minimum-volume threshold (argument, default 5).
5. `brRef` across the dates that have exports (2026-10-21 to 2026-10-23) to show whether it is constant.
6. One stacked chart (MDRM-2a) of Widevine requests by security level with `brRef`, embedded in the report markdown; a `ChartError` is logged and the report is still written.

**Tests (no network, no real external services):**
- `test_l1_with_low_br_ref_is_flagged`.
- `test_fairplay_low_is_excluded_from_hd_loss_count`.
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
