# DRM funnel chart visual consistency — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `docs/guides/chart-guidelines.md`. After each task: set
> `SHA:` on the task line + tick the box, update the story status summary, add one line to your backlog/session-log file. Prerequisite: `chart-guide-code-alignment` CA-1 and CA-2.

---

## MV-1 — decision record

**Files to change / create:**
- `docs/guides/chart-guidelines.md` — new "Funnel charts" section with the decisions below.
- `src/lib/charts/theme.py` and `tests/lib/charts/test_theme.py` — only if a token is added.

**What to implement:**

1. Ask the user to confirm each decision (use `ask_user`; do not assume): gradients (guide says no: flat connectors in `faint` or low-alpha series colour), error-rate callout (use a `HeaderCell` with
   `Tone.NEGATIVE` instead of a bordered card), background and blue (keep `bg` and `series[0]`), legend (direct labels, one outside legend only when a stack has more than one series), watermark
   (never).
2. Decide whether `license_outcome` is share-only or offers `--share` / absolute, and whether `none` (no DRM) is shown in the DRM-type charts.
3. Record each decision as adopted / adapted / rejected with the reason. Treat `modified/` as direction only; do not commit those PNGs (about 5 MB each, watermarked).

**Tests:** docs-only, plus a token test if the theme changes.

**Commit:** `docs(charts): record funnel chart design decisions`

---

## MV-2 — shared DRM-type order, labels and colours

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` — one helper (order: widevine, fairplay, playready, none unless MV-1 says otherwise; display labels capitalised; colour per type).
- `investigations/ctap-smvod/tests/test_drm_funnel_charts.py`.

**What to implement:**

1. Today `drm_split` sorts by size and `license_outcome` sorts alphabetically, so the same type sits in different places. Add `ordered_drm_types(rows)` and use it in both builders.
2. Map `none` to the muted token and the DRM types to `series` colours by fixed index, so a type keeps its colour across charts and runs.
3. Unknown buckets sort last, never raise.

**Tests (no network, no real external services):**
- `test_drm_type_order_is_stable_across_charts` — both builders return the same label order for the same rows.
- `test_unknown_bucket_sorts_last` — an unexpected bucket still renders.

**Commit:** `refactor(ctap-smvod): share DRM type order across funnel charts`

---

## MV-3 — `drm_split`

**Files to change / create:**
- `src/lib/charts/stacked_bar.py` — `legend` option (`"auto"` default, `False` suppresses) and a per-bar colour override for single-series charts; labels for bars under `MIN_LABEL_SHARE` drawn above
  the bar.
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py`, `tests/lib/charts/test_stacked_bar.py`, `tests/test_drm_funnel_charts.py`.

**What to implement:**

1. Suppress the legend when there is one series (kind `vod` only); keep it when VOD and linear both exist.
2. Draw `none` muted; the others use their MV-2 colours.
3. Give bars under 5% of the longest a label above the bar plus a minimum drawn height so playready stays visible.

**Tests (no network, no real external services):**
- `test_single_series_has_no_legend`, `test_small_bar_label_above_bar`, `test_invalid_legend_option_raises_chart_error`.

**Commit:** `feat(charts): single-series bar without legend, visible tiny bars`

---

## MV-4 — `license_outcome`

**Files to change / create:**
- `src/lib/charts/stacked_bar.py` — `normalise: bool = False` (each stack scaled to 100%; label shows share, subtitle or label carries the absolute count) and a legend placed above the plot, outside
  the bars.
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py`, tests for both.

**What to implement:**

1. Collapse the seven series to success / failed / no_request (green / red / muted); keep the error split as a second table or in the markdown, not in colour (the amber and pink series carry no
   meaning).
2. Add `normalise`; guard against zero-total stacks (raise `ChartError` or draw empty, decide in MV-1).
3. Axis shows `0%`..`100%` via `format_pct`; the absolute total per type goes under each x label.

**Tests (no network, no real external services):**
- `test_normalised_stacks_sum_to_100`, `test_zero_total_stack_handled`, `test_legend_outside_plot_area`.

**Commit:** `feat(charts): share-of-total stacked bars for license outcome`

---

## MV-5 — `stages`

**Files to change / create:**
- `scratch/funnel_stages/` — prototype first (`scratch/SCRATCH.md` convergence rule, duplicate-check stub), then promote to `investigations/ctap-smvod/scripts/lib/` (investigation-local unless a
  second investigation needs it).
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` and tests.

**What to implement:**

1. Fix clipping: size the left margin from the longest label (pure helper, tested) rather than a fixed `MARGIN_LEFT`.
2. Colour by meaning: Sessions and DRM requested neutral series colour, License success `green`, Ended in error `red`.
3. Add step conversion between stages (pure function: `-46.5%` drop to DRM requested, `98.9%` requested to success) using the same numbers as `stage_totals`.
4. Add a header with the error rate (`Tone.NEGATIVE`) and session count via `draw_header`; no gradients, no card border.
5. Note: "License success" is a share of sessions (52.9%), the conversion step is a share of DRM requested (98.9%); label both bases so they are not confused.

**Tests (no network, no real external services):**
- `test_step_conversion_rates`, `test_left_margin_fits_longest_label`, `test_stages_chart_returns_png`, `test_zero_sessions_raises_chart_error`.

**Commit:** `feat(ctap-smvod): funnel stages chart with step conversion`

---

## MV-6 — remaining charts, regenerate, guide

**Files to change / create:**
- `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` — `error_codes` and `3016_subcategory` use the same title block, colours and header cells (the 3016 donut follows
  `chart-pie-donut-rework` if that story has landed).
- `docs/guides/chart-guidelines.md` — final funnel conventions; `investigations/ctap-smvod/docs/usage.md` if flags changed.

**What to implement:**

1. Re-run `analyze_drm_funnel.py` for ZA, GH and ZM and view every PNG.
2. Check one consistency list across all five charts: title block, subtitle, DRM-type order and colours, legend rule, label sizes, error rate shown in the same colour everywhere.
3. User reviews the rendered PNGs; record the outcome and delete or archive the `modified/` mockups (do not commit them).

**Tests:** existing suite green; regenerate only, no new pixel tests.

**Commit:** `feat(ctap-smvod): consistent look across DRM funnel charts`
