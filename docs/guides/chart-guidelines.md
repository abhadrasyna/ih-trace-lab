# Chart Guidelines (matplotlib)

Standard for every generic plot rendered in this repo (investigation reports, PNG exports, scratch PoCs that may be promoted). It is adapted from NiftyShield's `docs/reference/chart_guidelines.md`
(accepted payoff chart, 2026-10-13). No chart code exists here yet, so this guide is the spec: when the first shared chart module lands (a `ChartTheme` in `src/lib/`), the code becomes the truth and
this doc must be fixed to match it.

## Palette and fonts (default)

Dark-only; there is no light variant. Once a shared `ChartTheme` exists, every colour comes from it and nowhere else.

| Token | Hex | Use |
|---|---|---|
| `bg` | `#0e1117` | Figure and axes background; also the fill of "hole" markers and label backing boxes |
| `ink` | `#e5e7eb` | Primary text, reference lines, markers, emphasis |
| `muted` | `#9ca3af` | Tick labels, zero/baseline line |
| `faint` | `#1f2937` | Grid, spines, secondary vertical guides |
| `green` | `#26b3a0` | Good / positive series |
| `red` | `#ef5350` | Bad / negative series (errors, failures) |

Area fills reuse the line colour with alpha: `fill_alpha_green = 0.22`, `fill_alpha_red = 0.14` (the bad side is deliberately quieter). Font is Roboto when bundled, resolved only through one
`chart_font_family()` helper that falls back to `"DejaVu Sans"` and never raises.

Type scale (pt): title 16 bold, subtitle 10, stat label 8.5, stat value 12 bold, stat sub 9, tick labels 9.5, annotations 9-10.

## Do

- Take every colour from a theme object. A new semantic colour is added to the theme (and its tests), not written inline.
- Get the font family once and pass `family=` to every text artist, including tick labels (`set_xticklabels(..., family=family)`).
- Build figures object-oriented and headless: `Figure(figsize=..., facecolor=theme.bg)` + `FigureCanvasAgg(fig)`. No `pyplot`, no global state, nothing to `plt.close()`.
- Save with `fig.savefig(buf, format="png", dpi=170, facecolor=theme.bg)` into a `BytesIO` and return `bytes`; the caller owns file I/O. Base size is 7 x 4.9 in; grow the height (5.7) when the header
  wraps to a second row.
- Keep chrome quiet: hide top and right spines, colour left and bottom spines `faint`, ticks `length=0` in `muted`, horizontal-only grid in `faint` at `lw=0.6` with `set_axisbelow(True)`.
- Colour by meaning, not by series: where a series has a good/bad sign (e.g. success vs error rate), use line `lw=1.8` with `solid_capstyle="round"`, split with `np.ma.masked_where` so green and red
  never overlap, and `fill_between(..., interpolate=True, lw=0)`. Neutral series use `ink`, `muted` or `faint`.
- Draw a zero/baseline with `axhline(0, color=muted, lw=0.7)`; vertical reference lines in `ink` at `lw=0.9`; secondary guides dotted (`ls=":"`, `lw=0.8`) in `faint`.
- Label with `annotate` using `textcoords="offset points"` so offsets survive resizing. Back overlapping labels with `bbox={"fc": theme.bg, "ec": "none", "pad": 1.5}`.
- Use "hole" markers for levels (`color=theme.bg, mec=theme.ink, ms=5, mew=1.1`) and a filled `ink` dot (`ms=8`) for the current value. Set `zorder` explicitly (markers 5-6, reference line 4).
- Abbreviate large counts on axes (`k`, `M`) through one shared formatter; format percentages consistently. Convert `float` to `Decimal` only at the display edge via `Decimal(str(v))` if a value is
  money.
- Compute data (ranges, ticks, bucketing, rates) in pure, separately tested helpers; keep drawing functions thin. Split by responsibility: theme, axes maths and draw helpers, header.
- Make chart output additive and non-fatal: a failed chart must never block the CSV/XLSX or text report it accompanies, and only a project error (not a matplotlib or numpy type) may escape.
- Test offline: assert on theme tokens, pure axis maths and that the output starts with the PNG magic bytes (`\x89PNG`). Never compare pixels against a golden image.

## Don't

- Don't write hex strings, named colours (`"red"`) or matplotlib default colour cycles (`C0`..`C9`) in drawing code.
- Don't use `matplotlib.pyplot` (`plt.subplots`, `plt.figure`, `plt.show`, `plt.savefig`) in `src/` or `scripts/`. It drags in global state, a GUI backend and figure-leak bugs.
- Don't rely on matplotlib's default font, and don't call `font_manager.addfont` outside `chart_font_family()`.
- Don't add a light theme, gradients, drop shadows, 3D, or chart borders. Don't add a legend when direct labels do the job.
- Don't use a rainbow or more than two hues for a signed series. Green and red carry sign; everything else is `ink`, `muted` or `faint`.
- Don't draw a full box grid, vertical gridlines, or visible tick marks. Don't use thick lines (> 2 pt) or tiny markers (< 5 pt).
- Don't call `savefig` to disk inside reusable render functions (return bytes; the script owns I/O).
- Don't use `tight_layout()` for the headered layout. Use explicit `subplots_adjust` margins (`left=0.13`, `right=0.97`, plus top and bottom values for one or two header rows) so the header geometry
  stays deterministic.
- Don't hold a `Figure` beyond the render call.

## Planned module layout

Planned in `docs/plan/shared-chart-infra/` and not yet built. One package, `src/lib/charts/`, split by responsibility with one-way dependencies (`signed_line`/`bar` → `axes`/`header`/`fig` → `theme`):

| Module | Holds |
|---|---|
| `theme.py` | Frozen `ChartTheme`, `DARK`, `chart_font_family()` |
| `fig.py` | Figure creation and the PNG-bytes save recipe |
| `axes.py` | `style_axes`, count/percentage formatters, pure tick and range maths |
| `header.py` | Optional stat header: `Tone`, `HeaderCell`, one- or two-row layout |
| `signed_line.py`, `bar.py` | Thin drawing functions that return PNG bytes |
| `errors.py` | `ChartError`, the only exception that leaves the package |

Rules from `docs/refactor/`: wrap third-party exceptions at the module boundary (matplotlib and numpy errors become `ChartError`), keep `theme` free of imports from the rest of the package, and prefer
`Protocol` over an abstract base if a chart interface is ever needed. Fonts: Roboto is bundled under `src/lib/charts/assets/fonts/` (Apache 2.0); `chart_font_family()` is cached, lock-guarded and
falls back to DejaVu Sans with a logged warning, never a raise. The header is optional: a chart without cells renders a plain title.

## Using charts from an investigation

Any investigation script follows the same shape:

1. Compute the plotted values in a pure, tested function (counts, rates, ranges); no drawing there.
2. Call one shared `render_*` function with plain lists and a title; it returns PNG `bytes`.
3. The script owns file I/O: write to the investigation's `output/<TENANT>/` folder, alongside the CSV/XLSX it accompanies.
4. Catch `ChartError`, log it and carry on; a failed chart must never block the CSV, XLSX or text report.

Worked example: `investigations/ctap-smvod/scripts/chart_concurrent_playback.py` (pilot, CH-6) composes `new_figure`, `draw_header`, `style_axes` and `render_png` directly for a three-series line
chart, because `render_signed_line` and `render_bar` draw a single series with no header; `write_chart` shows the `ChartError` handling.

Prototype new chart shapes in `scratch/` first (`SCRATCH.md` convergence rule) and promote into `src/lib/charts/` only once a second investigation needs them. The synchronous render needs no
`asyncio.to_thread`; use it only when a chart is rendered inside an async service.

## Adapting to a new chart type

Reuse the theme, `chart_font_family()`, a shared `style_axes()` and the figure/save recipe above unchanged. Only the data layer and the annotations are new. If a chart genuinely needs a token the
theme lacks (a third semantic colour, say), add it to the theme with a test and a row in the table above in the same commit.

## Provenance

Palette, type scale and recipe come from NiftyShield (`docs/reference/chart_guidelines.md`, reference implementation `src/notifications/payoff_chart*.py` there). NiftyShield-only rules (`₹` money
helpers, Telegram delivery, `RenderError`, `asyncio.to_thread`) were dropped or generalised here.
