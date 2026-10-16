# Shared chart infra — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Standards: `AGENTS.md` and `docs/guides/chart-guidelines.md`. After each task: set `SHA:` on the task line
> and tick the box, update the story status, add one line to the backlog/session log.

Dependency direction (one way only): `charts (signed_line, bar) → axes, header, fig → theme`. `theme` imports nothing from the package. Prototype in `scratch/` first (`SCRATCH.md`); promote only
proven code.

---

## CH-1 — Theme and font

**Files to change / create:**
- `src/lib/charts/__init__.py` — package marker.
- `src/lib/charts/theme.py` — frozen `ChartTheme` (`bg, ink, muted, faint, green, red, fill_alpha_green, fill_alpha_red`), `DARK` with the guide's hex values, `chart_font_family()`.
- `src/lib/charts/assets/fonts/Roboto-Regular.ttf`, `Roboto-Bold.ttf` — Apache 2.0, with a `LICENSE` file beside them.
- `tests/lib/charts/test_theme.py`.

**What to implement:**

1. Port `ChartTheme`/`DARK` from NiftyShield `payoff_chart_theme.py`.
2. `chart_font_family()` is cached and lock-guarded; it registers the bundled Roboto and returns `"Roboto"`. On any failure it logs a warning and returns `"DejaVu Sans"`; it never raises.
3. Log through the project's logging setup per `AGENTS.md`.

**Tests (no network):**
- `test_dark_tokens_match_guide` — hex values and alphas equal the guide's table.
- `test_font_falls_back_when_missing` — a missing font dir returns `"DejaVu Sans"` and does not raise.

**Commit:** `feat(charts): add ChartTheme and font fallback`

---

## CH-2 — Figure recipe and axes

**Files to change / create:**
- `src/lib/charts/fig.py` — `new_figure(theme, height=4.9)` returns `Figure` with `FigureCanvasAgg`; `render_png(fig, theme) -> bytes` (`dpi=170`, `BytesIO`).
- `src/lib/charts/axes.py` — `style_axes(ax, theme, family)`, `format_count(v)` (k/M), `format_pct(v)`, pure tick/range helpers.
- `tests/lib/charts/test_fig.py`, `tests/lib/charts/test_axes.py`.

**What to implement:**

1. Figure built with the object-oriented API only; base size 7 × 4.9 in, 5.7 in with a two-row header; explicit `subplots_adjust` margins, never `tight_layout`.
2. `style_axes` follows the guide: hidden top and right spines, `faint` left and bottom spines, `length=0` ticks in `muted`, horizontal `faint` grid at `lw=0.6`, `set_axisbelow(True)`.
3. Formatters are pure and take plain numbers; no money formatter (investigations chart counts and rates).

**Tests:**
- `test_render_png_magic_bytes` — output starts with `\x89PNG`.
- `test_format_count_abbreviates` — `1500 → "1.5k"`, `2_000_000 → "2M"`, negatives and zero handled.

**Commit:** `feat(charts): add figure recipe and axes styling`

---

## CH-3 — Chart types and error boundary

**Files to change / create:**
- `src/lib/charts/errors.py` — `ChartError`.
- `src/lib/charts/signed_line.py`, `src/lib/charts/bar.py` — thin drawing functions over pure data helpers.
- `tests/lib/charts/test_signed_line.py`, `tests/lib/charts/test_bar.py`.

**What to implement:**

1. `render_signed_line(xs, ys, *, title, subtitle="") -> bytes`: green above zero and red below via `np.ma.masked_where`, `fill_between(..., interpolate=True, lw=0)`, zero line in `muted`.
2. `render_bar(labels, values, *, title, subtitle="") -> bytes`: neutral `ink`/`muted` bars; sign colours only for signed series.
3. Wrap the body in `try/except Exception` and raise `ChartError` (guide: no matplotlib or numpy types escape); log the byte count.
4. Reject empty or mismatched-length input with `ChartError` before drawing.

**Tests:**
- `test_signed_line_returns_png` and `test_bar_returns_png`.
- `test_mismatched_lengths_raise_chart_error`, `test_empty_input_raises_chart_error`.

**Commit:** `feat(charts): add signed line and bar charts`

---

## CH-4 — Stat header (optional layout)

**Files to change / create:**
- `src/lib/charts/header.py` — `Tone(str, Enum)`, `HeaderCell`, size constants, cell packing and `draw_header(...) -> rows`.
- `tests/lib/charts/test_header.py`.

**What to implement:**

1. Port the packing logic from NiftyShield `payoff_chart_header.py`, minus payoff-specific cell builders.
2. Tone maps to `theme.green/red/ink/muted`; one row up to the width budget, otherwise two rows (caller then grows the figure to 5.7 in).
3. Charts accept an optional list of `HeaderCell`; without one they render a plain title.

**Tests:**
- `test_packing_one_row_vs_two_rows` — pure packing function, no rendering.
- `test_tone_uses_theme_colours` — no hex literal outside the theme.

**Commit:** `feat(charts): add stat header layout`

---

## CH-5 — Tests, dependencies, guard

**Files to change / create:**
- `requirements.txt` — pin `matplotlib` and `numpy`.
- `tests/lib/charts/test_guard.py`.
- `tests/lib/charts/__init__.py` as required by the package rule.

**What to implement:**

1. Pin versions after installing into the local `.venv`.
2. Guard test scans `src/lib/charts/*.py` and `scripts/` for `matplotlib.pyplot` and for `#rrggbb` literals outside `theme.py`.

**Tests:**
- `test_no_pyplot_in_src_or_scripts`, `test_no_hex_outside_theme`.

**Commit:** `test(charts): add guard tests and pin chart deps`

---

## CH-6 — Pilot adoption

**Files to change / create:**
- One script in the chosen investigation (proposed: `investigations/ctap-smvod/scripts/`; confirm the pilot at task start) — render one chart next to its report, additive and non-fatal.
- That investigation's `docs/usage.md`, and an entry in the workspace `SCRIPTS.md` registry per the scripts rule in `AGENTS.md`.

**What to implement:**

1. Script computes data in a pure function, calls the shared renderer, writes the bytes to `output/<TENANT>/`.
2. A `ChartError` is logged and the script continues; CSV/XLSX output is never blocked.
3. Add a "how to chart from an investigation" example to the chart guide.

**Tests:**
- `test_chart_failure_does_not_block_report` — renderer patched to raise `ChartError`; report still written.

**Commit:** `feat(ctap-smvod): add pilot chart via shared chart infra`

---

## CH-7 — Docs alignment

**Files to change / create:**
- `docs/guides/chart-guidelines.md` — replace "no chart code exists yet" with the real module names; keep the palette table in sync with `theme.py`.
- `CONTEXT.md` — "What Exists" entry for `src/lib/charts/`.

**What to implement:**

1. Update the guide to the code as the guide itself requires.
2. State that other investigations adopt the layer in their own stories.

**Tests:** none (docs only).

**Commit:** `docs(charts): align chart guide with shared module`
