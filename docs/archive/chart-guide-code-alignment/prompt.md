# Chart guide and code alignment — prompt

> Base story for chart improvement: make `src/lib/charts/` match `docs/guides/chart-guidelines.md` (and vice versa) before the per-chart polish stories build on it.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

A 2026-10-25 review of the guide, the shared chart package and the rendered ctap-smvod PNGs found drift between them. The guide's type scale says title 16 bold, but `bar`, `signed_line`, `stacked_bar`
and `pie` each hard-code a 13 pt title and a copy of the same title/subtitle block. `render_stacked_bar` abbreviates segment labels (`1.9k`) but leaves raw axis ticks (`2000`), against the guide's
"one shared formatter" rule. `CONTEXT.md` still says no chart code exists.

The per-chart polish stories (stacked-bar readability, pie/donut rework, concurrent-playback polish, playback-attempts polish) all touch the title block and axis formatting, so the shared pieces are
fixed once here to avoid four conflicting edits. Further guidelines are still to be discussed and will be folded into this story (as extra tasks) or a follow-up before work starts.

## Scope guard

In bounds: `src/lib/charts/` (new shared title helper, `stacked_bar.py`, `bar.py`, `signed_line.py`, `pie.py`), `tests/lib/charts/`, `docs/guides/chart-guidelines.md`, `CONTEXT.md`. Out of bounds:
ctap-smvod chart scripts and `drm_funnel_charts.py` (they call the shared package and need no change unless an API breaks), new chart types, legend/colour/layout redesign (later stories). Runtime
behaviour changes only visually (title size, axis tick text); public `render_*` signatures stay the same.

## Session-start load hints

- `docs/guides/chart-guidelines.md` (type scale, Do/Don't, module layout) and `src/lib/charts/` (all modules) plus `tests/lib/charts/test_guard.py`.
- `docs/archive/shared-chart-infra/stories.md` for the original conventions.

## Task overview

- **CA-1** — one shared `draw_title` helper (16 pt bold title, 10 pt subtitle) used by every chart module.
- **CA-2** — shared count/percent axis formatting applied to bar and stacked-bar value axes.
- **CA-3** — align `chart-guidelines.md` and `CONTEXT.md` with the code and remove stale statements.

## Definition of done

Mirrors `tasks.md` "Story done when": no chart module hard-codes title or subtitle text styling; value axes use the shared formatters; guide and `CONTEXT.md` match the code; suite green offline.

## Perspectives not covered

- Visual regression: tests assert tokens and PNG magic bytes only (per the guide), so a title that overflows the figure at 16 pt is caught by eye on a re-render, not by a test.
- Headered layouts (`draw_header`) already place their own text; whether stacked-bar/pie should gain a header is left to the polish stories.
