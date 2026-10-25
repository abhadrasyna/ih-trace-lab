# DRM funnel chart visual consistency — prompt

> Bring the ctap-smvod DRM funnel charts (`stages`, `drm_split`, `license_outcome`, then the rest) to the improved look in `output/ZA/charts/modified/`, consistently across all of them and within the
> guide.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`investigations/ctap-smvod/output/ZA/charts/modified/` holds three mockups (`stages`, `drm_split`, `license_outcome`) that look better than the shipped PNGs in `output/ZA/charts/`. A side-by-side
review on 2026-10-25 found they are AI-generated design direction, not a spec: each is about 5 MB and carries a watermark, `license_outcome` uses placeholder percentages (70/15/15, 50/35/15, 40/20/40)
and a lighter navy background and larger regular-weight title than the other two. Matching them pixel for pixel would copy those inconsistencies.

What the mockups get right, and the shipped charts lack:
- **stages**: a funnel shape with step conversion between stages (-46.5%, 98.9%), a separate "ended in error" KPI (42.3%), and no clipped labels. The shipped chart is four same-colour horizontal bars
  whose y labels are cut off ("DRM requested", "License success"), with "ended in error" in the same blue as the success stages.
- **drm_split**: the "none" (no DRM) bar is muted grey, so it reads as "not a DRM type"; the shipped chart has all bars one blue and a pointless "vod" legend for a single series.
- **license_outcome**: success/failed/no_request in green/red/grey, one clear legend outside the plot, shares normalised to 100% so DRM types are comparable. The shipped chart has seven series with
  palette colours that carry no meaning (success-error amber, failed-error pink), a legend over the bars, and the tiny playready bar is invisible.

## Conflicts with `docs/guides/chart-guidelines.md` (decide in MV-1, do not copy blindly)

- Funnel connectors use gradients; the guide forbids gradients.
- The error-rate card has a coloured border and amber fill; the guide forbids chart borders and offers `HeaderCell`/`Tone` for stat callouts.
- The mockup background and saturated blue are not the `bg` / `series[0]` tokens; every colour must come from `ChartTheme`.
- Mockup legends sit beside the subtitle; the guide prefers direct labels and no legend where they do the job.

## Scope guard

In bounds: `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` and its tests, `scripts/analyze_drm_funnel.py` only if the chart set changes, shared additions to `src/lib/charts/` that a
second chart needs, `docs/guides/chart-guidelines.md`. Out of bounds: `chart_concurrent_playback.py`, `chart_playback_attempts.py` (own polish stories), the funnel numbers themselves
(`lib/drm_funnel.py`), committing the mockup PNGs. Depends on `chart-guide-code-alignment` CA-1 and CA-2 (shared title helper, axis formatting) being done first.

## Session-start load hints

- `docs/guides/chart-guidelines.md`, `src/lib/charts/stacked_bar.py`, `header.py`, `pie.py`, `investigations/ctap-smvod/scripts/lib/drm_funnel_charts.py` and `tests/test_drm_funnel_charts.py`.
- View the `modified/` PNGs and the matching shipped ones before each task.

## Task overview

- **MV-1** — decision record: mockup vs guide conflicts, token additions, normalised-share rule.
- **MV-2** — shared ordering, labels and colour mapping for DRM types across all funnel charts.
- **MV-3** — `drm_split`: muted `none`, no single-series legend, visible tiny bars.
- **MV-4** — `license_outcome`: 100% share mode, three semantic series, legend outside the plot.
- **MV-5** — `stages`: scratch funnel prototype, fixed labels, colour by meaning, step conversion, error-rate header.
- **MV-6** — apply the same conventions to `error_codes` and `3016_subcategory`; regenerate ZA/GH/ZM and review.

## Definition of done

Mirrors `tasks.md` "Story done when". Every funnel chart for ZA, GH and ZM uses the same DRM-type order, labels, colour mapping, title block and background, and the guide documents the funnel
conventions.

## Perspectives not covered

- Share-only (100%) bars hide absolute volume; MV-4 puts absolute counts in labels or the subtitle, and whether to also keep an absolute variant is a decision for MV-1.
- A true funnel/trapezoid chart type may not justify promotion into `src/lib/charts/` until a second investigation needs it (guide convergence rule), so it may stay investigation-local.
- No pixel-diff testing; visual acceptance is a manual re-render review by the user.
