# Shared chart infra — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CH-5, CH-6, CH-7.**

- [x] **CH-1** — `src/lib/charts/theme.py`: `ChartTheme`, `DARK`, `chart_font_family()`; bundle Roboto | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: fb34d8e
- [x] **CH-2** — `fig.py` figure/save recipe and `axes.py` `style_axes`, formatters, tick maths | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: 85ccb7d
- [x] **CH-3** — `signed_line` and `bar` chart types; `ChartError` boundary | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: 402af09
- [x] **CH-4** — `header.py`: `Tone`, `HeaderCell`, one- or two-row layout | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: f0b82dc
- [ ] **CH-5** — offline tests, pinned `matplotlib`/`numpy`, guard test (no `pyplot`, no inline hex) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —
- [ ] **CH-6** — pilot chart in one investigation; `usage.md` and `SCRIPTS.md` entries | Owner: Copilot CLI + user | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **CH-7** — align `chart-guidelines.md` with the code; update `CONTEXT.md` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **CH-1** — every colour and the font family come from `theme.py`; the font loader never raises and falls back to DejaVu Sans.
- **CH-2** — a figure renders headlessly to PNG bytes with no `pyplot`; axes follow the guide's quiet-chrome rules.
- **CH-3** — callers get PNG bytes or a `ChartError`; no matplotlib or numpy exception type escapes.
- **CH-4** — a header of 1 to 6 cells renders in one or two rows with deterministic margins.
- **CH-5** — the suite passes offline; the guard test fails on `pyplot` or a hex literal outside `theme.py`.
- **CH-6** — the pilot investigation writes a PNG next to its report; a chart failure does not block the CSV/XLSX.
- **CH-7** — `chart-guidelines.md` no longer says "no chart code exists" and matches the module and function names.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `docs/plan/TODOS.md` and add one line to your backlog/session-log file. When the whole story is
done, archive it with `scripts/dev/archive_completed_story.py`.
