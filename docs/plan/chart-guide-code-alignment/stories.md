# Chart guide and code alignment — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md` and `docs/guides/chart-guidelines.md`. After each task: set
> `SHA:` on the task line + tick the box, update the story status summary, add one line to your backlog/session-log file.

---

## CA-1 — shared title helper at the guide's type scale

**Files to change / create:**
- `src/lib/charts/header.py` (or a new `title.py` if it keeps the dependency direction one-way: `signed_line`/`bar` → `axes`/`header`/`fig` → `theme`) — `draw_title(fig, title, subtitle, theme,
  family)`.
- `src/lib/charts/bar.py`, `signed_line.py`, `stacked_bar.py`, `pie.py` — replace the inline `fig.text` title/subtitle block with the helper.
- `tests/lib/charts/test_title.py` (or the matching existing test file), `tests/lib/charts/test_guard.py` if it should forbid inline title text.

**What to implement:**

1. Add `TITLE_FONT_SIZE = 16`, `SUBTITLE_FONT_SIZE = 10` constants and `draw_title`; colours from `theme` only, `family=` passed.
2. Replace the four duplicated blocks; keep the 0.13 left edge and the title/subtitle y positions unless 16 pt collides with the plot top (then adjust `MARGIN_TOP_PLAIN` in `fig.py`, once).
3. Re-render one ZA chart per type and look at it; a long title must not clip at the figure edge (decide wrap or truncate here, note in the guide).

**Tests (no network, no real external services):**
- `test_draw_title_sizes_and_colours` — title text artist has size 16, bold, colour `theme.ink`; subtitle size 10, colour `theme.muted`.
- `test_draw_title_without_subtitle` — only one text artist is added.
- Existing `render_*` tests still return PNG bytes.

**Commit:** `refactor(charts): share title helper at 16/10 pt scale`

---

## CA-2 — shared count formatter on value axes

**Files to change / create:**
- `src/lib/charts/bar.py`, `src/lib/charts/stacked_bar.py` — set the value-axis major formatter to `format_count` (y for vertical, x for horizontal).
- `tests/lib/charts/test_bar.py`, `tests/lib/charts/test_stacked_bar.py`.

**What to implement:**

1. Pull the formatter wiring into a small helper in `axes.py` (e.g. `format_value_axis(ax, horizontal)`) so ctap-smvod line charts can reuse it later instead of repeating the lambda.
2. Apply it in both chart types; bar currently has no formatter, stacked bar uses raw ticks.

**Tests (no network, no real external services):**
- `test_format_value_axis_vertical_and_horizontal` — the formatter lands on the correct axis and renders `2000 -> "2k"`.
- `test_stacked_bar_axis_labels_abbreviated` — tick labels from a rendered figure contain no 4-digit raw counts.

**Commit:** `fix(charts): abbreviate value-axis counts on bar charts`

---

## CA-3 — align guide and CONTEXT.md

**Files to change / create:**
- `docs/guides/chart-guidelines.md` — type scale and module table (new helper, constants), keep the 200-char line cap.
- `CONTEXT.md` — remove the stale "no chart code exists" bullet (the `docs/guides/chart-guidelines.md` entry near the tenant/query-catalog items) and mention this story's outcome.

**What to implement:**

1. Re-read the guide against the code after CA-1 and CA-2 and fix every mismatch (sizes, function names, `render_pie` `donut` parameter, `render_bar`/`render_signed_line` signatures).
2. Update `CONTEXT.md` "What Exists" in place.

**Tests (no network, no real external services):**
- Docs only; run the repo's markdown line-length/pre-commit hooks.

**Commit:** `docs(charts): align guide and CONTEXT with chart code`
