# Shared chart infra — prompt

> Delivers one shared, dark-theme matplotlib chart layer in `src/lib/charts/` that every investigation can call to render PNG charts.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`docs/guides/chart-guidelines.md` is a spec with no code behind it. Investigations (ctap-smvod, mtn-monthly-error-code-analysis, inc-latency-shaka-1xxx) each produce CSV/XLSX/markdown today and no
charts. If each one adds its own plotting, colours, fonts and figure/save recipe drift apart, which is the duplication `docs/refactor/code-deduplication-and-taxonomy.md` warns about.

The reference implementation is NiftyShield (`docs/reference/chart_guidelines.md`, `src/notifications/payoff_chart_theme.py`, `payoff_chart_axes.py`, `payoff_chart_header.py`, `payoff_chart.py`). Its
payoff-specific parts (strike ticks, breakevens, spot and "Now" markers, money formatters, Telegram delivery) are not carried over; the theme, font fallback, figure/save recipe, axes styling and
header layout are.

## Scope guard

- In bounds: new `src/lib/charts/` package and its tests, bundled Roboto font assets, pinned `matplotlib`/`numpy` in `requirements.txt`, `docs/guides/chart-guidelines.md`, `SCRIPTS.md`, `CONTEXT.md`.
- Out of bounds: rewriting any investigation's existing reports. Each investigation adopts the layer in its own later story. Exception: CH-6 adds one pilot chart to one investigation.
- Runtime behaviour: new library code only; no existing script changes outside CH-6.

## Session-start load hints

- `docs/guides/chart-guidelines.md` — the do/don't standard, palette and type scale (the spec until CH-7 makes the code the truth).
- `docs/refactor/code-deduplication-and-taxonomy.md` (Step 2: module map, dependency direction, wrap third-party exceptions at the boundary) and `docs/refactor/design-principles.md` (SRP/OCP/DIP,
  `Protocol` over ABC, EAFP).
- `SCRATCH.md` convergence rule: prototype in `scratch/` first, promote only what is proven.
- NiftyShield reference files listed above (read-only, at `/Users/abhadra/myWork/myCode/python/NiftyShield`).

## Task overview

- **CH-1** — `ChartTheme`, `DARK`, `chart_font_family()` and bundled Roboto.
- **CH-2** — figure/save recipe and `style_axes` + pure axis maths and formatters.
- **CH-3** — chart types (signed line, bar) and the `ChartError` boundary.
- **CH-4** — optional stat header (`Tone`, `HeaderCell`, one or two rows).
- **CH-5** — tests, pinned dependencies and a guard test against `pyplot` and inline hex.
- **CH-6** — pilot chart in one investigation, usage docs and `SCRIPTS.md`.
- **CH-7** — make `chart-guidelines.md` match the code; update `CONTEXT.md`.

## Definition of done

Mirrors `tasks.md` "Story done when": one importable package renders themed PNG bytes headlessly, is fully tested offline, has one investigation using it, and the guide matches the code.

## Perspectives not covered

- Light theme and interactive charts (guide forbids a light variant).
- Embedding charts inside XLSX or markdown reports; PNG bytes are the only output.
- Adoption by the other investigations; each needs its own story.
- Async or `to_thread` rendering; the investigation scripts are synchronous.
