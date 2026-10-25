# mDRM analysis and DRM session funnel (ctap-smvod) — prompt

> Add a daily session-to-license-to-error funnel and a set of mDRM export analyses to the ctap-smvod pipeline, first proven on 2026-10-23 for ZA, GH and ZM.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The pipeline links 3014/3015/3016 errors to DRM details (`ctap-smvod-3016-drm-device-link`), but nothing measures the mDRM exports themselves, and nothing answers the top-level question: of all
sessions created, how many asked for a DRM license, how many licenses succeeded or failed, and how many sessions then ended in a player error such as 3016. Review of the 2026-10-23 exports showed
`brRef=LOW` on every request (3,343 across GH, ZM and ZA), 29 mdrmfe `403` rows matching 29 LRM `400` rows, and no timestamps, error bodies or `deviceId` on the CDM exports, so the analyses must work
within those limits.

The funnel must run daily as a pipeline step, so it is a script plus a `run_pipeline.py` step, not a one-off analysis.

## Decisions taken (2026-10-25)

- **Session scope:** VOD (`abr-vod-*`) and linear (`abr-linear-*`) are both counted, with a VOD/linear split.
- **mDRM sessions missing from the CTAP/SMVOD merge:** counted in the funnel as extra sessions, marked with a `source` column (`merge` or `drm_only`) so the inflated count stays visible.
- **Cadence and sample:** runs daily; 2026-10-23 for ZA, GH and ZM is the sample and acceptance run.
- **Output:** a funnel CSV plus a short markdown summary per OpCo and date under `output/<OPCO>/`.

## Scope guard

- **In bounds:** `investigations/ctap-smvod/scripts/`, `scripts/lib/`, `tests/`, `docs/`, `data/lightstep/<OPCO>/` (read only), `output/<OPCO>/`, `run_pipeline.py`, plus root `SCRIPTS.md` and
  `CONTEXT.md`. For MDRM-2a only: `src/lib/charts/` (new stacked-bar chart and theme series palette), its tests and `docs/guides/chart-guidelines.md`.
- **Out of bounds:** the rest of `src/`, other investigations, any live Lightstep or Athena call from code (inputs are saved CSVs), changing how CTAP/SMVOD parts are combined (Step 1b stays as is).
- Runtime behaviour: adds one optional pipeline step; existing steps and outputs are unchanged.

## Session-start load hints

- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` — file names, attribute names, the `brRef` note and the join.
- `investigations/ctap-smvod/scripts/lib/drm_exports.py` — existing readers; `export_paths` reads a whole-day file plus all `_NN_` parts with no dedup.
- `output/<OPCO>/<date>_setupsession_with_outcome.csv` and `output/<OPCO>/error_eventdata_flat/<date>_all.csv` — session list and downstream error inputs.
- `docs/plan/ctap-smvod-3016-drm-device-link/` — the sibling story this one builds on.

## Task overview

- **MDRM-1** — pure funnel logic: unique sessions, DRM-type split, license outcome per type, downstream error per outcome.
- **MDRM-2** — funnel CLI: CSV plus markdown summary; first run on 2026-10-23 for ZA, GH, ZM.
- **MDRM-2a** — shared stacked-bar chart (theme series palette, `render_stacked_bar`) in `src/lib/charts/`, with the guide updated.
- **MDRM-2b** — funnel charts built on it and embedded in the funnel markdown summary.
- **MDRM-3** — license-chain quality: status-code split, the 403/400 failures, requests per session and retries, `fcId` consistency across exports, ZA part-overlap check.
- **MDRM-4** — device and policy analysis: `brRef` against Widevine security level, FairPlay devices, VOD against linear, failing devices and households, `brRef` across dates.
- **MDRM-5** — wire the funnel into `run_pipeline.py` as a daily step, plus `SCRIPTS.md` and `CONTEXT.md`.
- **MDRM-6** — docs: list the extra Lightstep attributes to export (timestamps, error body, CDM `deviceId`, token claims) and the findings of the 2026-10-23 sample.

## Definition of done

For 2026-10-23 the funnel CSV and summary exist for ZA, GH and ZM and reconcile (every session appears in exactly one DRM bucket and one license outcome); MDRM-3 and MDRM-4 reports are produced from
the same inputs; the funnel runs from `run_pipeline.py` with a skip flag; tests are green and offline; the registries and docs are updated.

## Perspectives not covered

- No timestamps in the mDRM exports, so latency, time-of-day clustering and token-to-license delay cannot be measured until the exports are re-saved with them (MDRM-6 lists this).
- The 29 `403`/`400` failures have no reason text; the analysis can describe who failed, not why.
- Counting `drm_only` sessions as funnel sessions can inflate the "sessions created" total; the `source` column is the only guard.
- PlayReady (19 rows on 2026-10-23, different attribute names, no security level) is reported but not analysed deeply.
