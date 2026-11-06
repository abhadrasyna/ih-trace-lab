# Chart Guidelines (matplotlib)

Standard for every generic plot rendered in this repo (investigation reports, PNG exports, scratch PoCs that may be promoted). It is adapted from NiftyShield's `docs/reference/chart_guidelines.md`
(accepted payoff chart, 2026-10-13). The shared code in `src/lib/charts/` is now the truth for the palette, figure recipe and module layout; this guide must be fixed whenever the code changes.

## Audience and principle

Charts are investigation evidence (counts, rates, error mix per tenant and day) written for an executive reader: the chart must carry the story on its own, so a reader gets the conclusion in seconds
without the accompanying text. Minimise cognitive load, maximise data-ink, and use colour for meaning, never decoration. Every chart states its base (what the percentages are a share of) in the title,
subtitle or label. Spelling in code and docs: `normalize` (US), as in `render_stacked_bar(..., normalize=True)`.

## Story charts (the default for new work)

A story chart answers one question and says the answer in its title. Every new chart is built with one of the story renderers below (`rate_bars`, `columns`, `trend`, `composition`); the older
renderers (`stacked_bar`, `bar`, `signed_line`, `pie`) stay for dense multi-series cases and share the same palette and rounded bars. Rules, in order of importance:

1. **Title = the finding**, a sentence with the number in it ("Newest households fail 65% of playbacks; the oldest 34%"), never a description of the chart. The title is computed from the data, so it
   changes when the data does (`more than doubled`, `held steady`, `fell`).
2. **Subtitle = the measure**: one line defining exactly what the bar or point is ("Share of playback attempts that did not succeed, by how long the household has been seen"). No dates, tenant or base
   here.
3. **Footer = scope**: one 8 pt line for tenant, date range, base and caveats (censoring, per-install ids). It is drawn by `title.draw_footer`.
4. **Direct labels, no legend, no KPI strip.** The value sits at the end of the bar or point, the category name sits on its bar or line. If a legend seems needed, the chart has too many series: split
   it.
5. **One left edge.** Title, subtitle, header, labels and footer share `LEFT_EDGE = 0.05` of the figure width.
6. **Chart type follows the data**: a few ranked categories use `rate_bars`; one value per period uses `columns`; change over time uses `trend` (indexed to 100 when the series differ in size); parts
   of one whole use `composition`. Axes appear only when they carry information (`trend` keeps a light value axis, the bar charts none).
7. **Colour carries meaning**: coral (`red`) is failure or the 6001 error, teal (`green`) is success or recovery, `violet` and `blue` are neutral categories, and `dim_<name>` is the "before" or the
   non-focus bar. Highlight one bar, dim the rest.
8. **No false precision**: one decimal for rates under 10%, none above; counts get thousands separators; percent change is rounded to whole numbers in titles.
9. **Say when the sample is small** in the footer (for example, recovery rests on 6 events), and never chart a rate without its count in the label.
10. Eight rows at most per bar chart and three series at most per trend; the renderer raises `ChartError` beyond that, so cut to the top N and say so in the title ("Top 6 device models carry 40%").

## Choosing a chart type

| Insight goal | Chart | Reasoning |
|---|---|---|
| Ranked categories, one measure | `render_rate_bars` | Label above or beside each bar, value at the end, faint track shows the scale. Up to 8 rows. |
| One value per period or day | `render_columns` | Latest period in full colour, earlier ones dimmed; value above each column. |
| Change over time, 1 to 3 series | `render_trend` | Straight segments, direct end labels, optional reference line; index to 100 when comparing sizes. |
| Share of a single whole | `render_composition` | One 100% bar with labelled segments; replaces a donut for 2 to 5 parts. |
| Pipeline and drop-off | Funnel (stages read top to bottom) | Absolute volume per stage, with step-to-step conversion annotated (e.g. 98.9% of the previous stage), not just totals. |
| Rates across segments of very different size | 100% stacked bar (`normalize=True`) | Compares success/failure/error efficiency, not scale; show absolute totals alongside so volume is not hidden. |
| Absolute volume across categories | Bar or horizontal bar, sorted descending | Rank is instant; horizontal when labels are long. |
| Trend and sign over time | Signed line | Green or red fill tells at a glance whether the trend is net good or bad. |
| Parts of a whole | Donut, 2 to 4 categories, small ones grouped as `other` | Total in the hole as the KPI; if one category dominates (e.g. error code 6001), use a horizontal bar. |

## Palette and fonts (default)

Dark-only; there is no light variant. Every colour comes from the shared `ChartTheme` and nowhere else; drawing code names a token (`"red"`, `"dim_blue"`) and resolves it with `resolve_colour(name,
theme)`. The palette is soft (pastel on a deep navy) so that large rounded shapes read as calm rather than loud.

| Token | Hex | Use |
|---|---|---|
| `bg` | `#0e1117` | Figure and axes background; also the fill of "hole" markers and label backing boxes |
| `ink` | `#e5e7eb` | Primary text, reference lines, markers, emphasis |
| `muted` | `#8b93a3` | Tick labels, labels above bars, zero/baseline line |
| `faint` | `#222937` | Grid, spines, bar tracks, secondary vertical guides |
| `green` | `#5ec8b4` | Good / positive series (success, recovery) |
| `red` | `#f0877f` | Bad / negative series (errors, failures) |
| `amber` | `#e9b872` | Warning: retries, non-fatal or degraded states (`Tone.WARNING`) |
| `series[0..4]` | `#7fa8f5`, `#a99bf0`, `#e79bc2`, `#8e9ab0`, `#d9b88f` | Ordered palette for multi-series charts (blue, violet, pink, slate, sand); `ChartTheme.series` |
| `dim_<name>` | blend of `<name>` towards `bg` (`dim_amount = 0.38`) | De-emphasised bars: the "before" period, non-focus columns. Built by `dim(colour, theme)` |
| `corner_radius_in` | 0.09 in | Corner radius of every bar, in inches so corners stay circular whatever the data scale |

`resolve_colour` accepts `ink`, `muted`, `faint`, `green`, `red`, `amber`, the series names `blue`, `violet`, `pink`, `slate`, `sand`, and a `dim_` prefix on any of them; anything else raises
`ValueError`.

`green`, `red` and `amber` are reserved for status (good, bad, warning): they never appear in `series`, and a multi-series chart gets them only by mapping a series to them explicitly (for example
`render_stacked_bar`'s `colours={"success": "green", "failed": "red", "retried": "amber"}`). Any other series takes the palette in order, cycling after five; a chart with more segments than it can
label needs a legend. `render_pie` defaults to `max_slices=5` (four categories plus `other`) and rejects more than the palette size.

Colour rules:
- Assign each recurring category one fixed colour across every chart of a report (e.g. a DRM type keeps its colour), so colours do not drift across an executive deck.
- Structural or null categories (`none`, `no_request`, `unprotected`, `other`) use `muted`, never a series colour, so the active data pops. Not `faint`: `#1f2937` on `bg` is almost invisible and
  `faint` stays for grid, spines and guides.
- Don't compress the active series by plotting a huge null column on the same absolute scale; dim it, label it directly, or separate it.

Area fills reuse the line colour with alpha: `fill_alpha_green = 0.22`, `fill_alpha_red = 0.14` (the bad side is deliberately quieter). Font is Roboto when bundled, resolved only through one
`chart_font_family()` helper that falls back to `"DejaVu Sans"` and never raises.

Type scale (pt): title 15 bold, subtitle 9.5, footer 8 (drawn only by `title.draw_title` and `title.draw_footer`; a title wider than the figure is truncated with an ellipsis, measured on the rendered
text), stat label 8.5, stat value 12 bold, stat sub 9, tick labels 9.5, annotations 9-10.

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
- Don't add a light theme, gradients, drop shadows, 3D, or chart borders. Bars are rounded (`add_bars`/`RoundedBar`), never sharp rectangles: don't call `ax.bar`/`ax.barh` in new code. Don't add a
  legend when direct labels do the job.
- Don't use emoji, icons or pictographs; clean typography and geometric shapes only. Don't keep a legend for a single series or when segments are large enough for direct labels.
- Don't use a rainbow or more than two hues for a signed series. Green and red carry sign; everything else is `ink`, `muted` or `faint`. Multi-series charts (not signed) use the `series` palette.
- Don't draw a full box grid, vertical gridlines, or visible tick marks. Don't use thick lines (> 2 pt) or tiny markers (< 5 pt).
- Don't call `savefig` to disk inside reusable render functions (return bytes; the script owns I/O).
- Don't use `tight_layout()` for the headered layout. Use explicit `subplots_adjust` margins (`left=0.13`, `right=0.97`, plus top and bottom values for one or two header rows) so the header geometry
  stays deterministic.
- Don't hold a `Figure` beyond the render call.

## Module layout

Built by `docs/archive/shared-chart-infra/`. One package, `src/lib/charts/`, split by responsibility with one-way dependencies (`signed_line`/`bar`/`stacked_bar`/`pie` → `title`/`axes`/`header`/`fig`
→ `theme`):

| Module | Holds |
|---|---|
| `theme.py` | Frozen `ChartTheme`, `DARK`, `dim`, `resolve_colour`, `chart_font_family()` |
| `fig.py` | Figure creation and the PNG-bytes save recipe |
| `axes.py` | `style_axes`, `format_count`/`format_pct`, `format_value_axis` (abbreviates value-axis ticks, e.g. `2k`), pure tick and range maths |
| `shapes.py` | `RoundedBar` patch (corners stay circular on screen), `add_rounded_bar`, `add_bars` (the `bar`/`barh` replacement; the caller sets the axes limits) |
| `title.py` | `draw_title` (15 pt bold title, 9.5 pt subtitle) and `draw_footer` (8 pt scope line); `LEFT_EDGE` is the shared left edge. Every chart module calls them, none draws its own |
| `canvas.py` | The story-chart drawing surface: a full-figure axes in inches (`new_canvas`, `frame`, `finish`, `Canvas.text/bar/hline`), shared layout constants and `require_values` |
| `rate_bars.py`, `columns.py`, `trend.py`, `composition.py` | Story renderers (`render_*`); take frozen dataclasses (`RateRow`, `Column`, `TrendSeries`, `Part`), raise `ChartError` on bad input |
| `header.py` | Optional stat header: `Tone`, `HeaderCell`, one- or two-row layout |
| `signed_line.py`, `bar.py` | Thin drawing functions returning PNG bytes: `render_signed_line(xs, ys, *, title, subtitle="", theme=DARK)`, `render_bar(labels, values, *, title, ...)` (same kwargs) |
| `stacked_bar.py` | `render_stacked_bar`: one stack per label; segment labels, optional legend (see below) |
| `pie.py` | `render_pie`: donut with the total in the centre and a legend below; small slices merge into `other` |
| `errors.py` | `ChartError`, the only exception that leaves the package |
| `output.py` | `write_chart_png` / `chart_path`: saves PNGs under `<output>/<TENANT>/charts/`, creating the folder on first use |

`render_stacked_bar(labels, series, *, title, subtitle="", footer="", horizontal=False, colours=None, bar_colours=None, total=None, normalize=False, legend="auto", theme=DARK)` takes `series` as a
name-to-values map with one value per label. Each segment is labelled with its value, plus its share when `total` is given. `normalize=True` scales each stack to 100% (axis `0%`..`100%`, labels show
the count and its share of that stack, a zero-total stack is drawn empty); put absolute totals in the labels. `legend="auto"` draws a legend inside the plot only for more than one series, `"above"`
puts it above the plot outside the bars, `False` never draws one, and any other value raises `ChartError`. `bar_colours` (hex colours derived from the theme, one per label, single series only) colours
each bar separately. In a single-series chart a bar under 5% of the longest is labelled above the bar, and one under 2% is also lifted to that minimum drawn height. Input that is empty, unequal in
length, negative or non-finite raises `ChartError`.

`render_pie(labels, values, *, title, subtitle="", donut=True, max_slices=5, theme=DARK)` draws a donut (a full pie with `donut=False`) and a legend below it. Slices beyond `max_slices - 1` merge into
a muted `other` slice. Use it only for a handful of parts of a whole where no slice dominates; when one category is most of the total (e.g. error code 6001), use a horizontal bar instead. Empty,
unequal, negative or non-finite input raises `ChartError`.

**Planned, not in code yet** (do not rely on this until the owning task lands): a `render_horizontal_bar` sorted descending (promote when a second chart needs it). The funnel stages chart with step
conversion exists investigation-local (`investigations/ctap-smvod/scripts/lib/funnel_stages_chart.py`); promote it to `src/lib/charts/funnel.py` only once a second investigation needs it.

Rules from `docs/refactor/`: wrap third-party exceptions at the module boundary (matplotlib and numpy errors become `ChartError`), keep `theme` free of imports from the rest of the package, and prefer
`Protocol` over an abstract base if a chart interface is ever needed. Fonts: Roboto is bundled under `src/lib/charts/assets/fonts/` (Apache 2.0); `chart_font_family()` is cached, lock-guarded and
falls back to DejaVu Sans with a logged warning, never a raise. The header is optional: a chart without cells renders a plain title.

## Funnel charts

Decision record for the DRM funnel charts (story `chart-funnel-visual-consistency`, decided 2026-10-25). The mockups in `output/ZA/charts/modified/` are AI-generated design direction, not a spec: they
are about 5 MB each, carry a watermark and one uses placeholder percentages. They are never committed.

| Mockup trait | Decision | Reason |
|---|---|---|
| Lighter navy background, saturated blue | Rejected | Every colour comes from `ChartTheme`: keep `bg` and `series[0]`. |
| Watermark | Rejected | Never drawn. |
| Gradient funnel connectors | Adapted | Flat `muted` connectors; the guide forbids gradients. |
| Error-rate card with coloured border and amber fill | Adapted | A `HeaderCell` with `Tone.NEGATIVE`; no borders or cards. |
| Legend beside the subtitle | Adapted | One legend above the plot, outside the bars, only when series carry meaning (success, failed, no_request). No legend for a single series. |
| Muted grey `none` bar | Adopted | `none` (no DRM) is a null category: `muted`, and it stays visible in DRM-type charts. |
| `license_outcome` as 100% bars, green/red/muted | Adopted | `normalize` makes DRM types comparable; the three outcomes are the only series. The error split stays in the markdown tables. |
| Absolute volume | Adapted | `license_outcome` defaults to share of DRM type with the absolute total under each x label; `--absolute` on `analyze_drm_funnel.py` draws raw counts. |
| Funnel shape with step conversion, separate error-rate KPI, no clipped labels | Adopted | Built in MV-5. |

Rules for every funnel chart:

- DRM types appear in one fixed order (widevine, fairplay, playready, none; unknown buckets last), with capitalised display labels and a fixed colour per type, so a type looks the same in every chart.
- A share-of-total stack (`normalize=True`) scales each stack to 100%; a stack whose total is zero is drawn empty (no segments, no label), never an error or a division by zero.
- A bar under 5% of the longest has its label drawn above it, and under 2% it is also lifted to a minimum drawn height; in a horizontal single-series bar the threshold is 25%, so "count (share)" text
  never overruns the bar.
- The `stages` chart sizes its left margin from the longest label, colours stages by meaning (neutral series colour for volume, `green` license success, `red` ended in error), annotates step
  conversion between bars and names each base (`-46.5% vs sessions`, `98.9% of DRM requested`; bar labels are shares of all sessions).
- Error rate is always a `HeaderCell` with `Tone.NEGATIVE` (red) under the title block, drawn by `draw_header(..., y_shift=UNDER_TITLE_SHIFT)`; `render_stacked_bar(header=...)` does the same and
  cannot be combined with `legend="above"`. Used by `stages` and `error_codes`.
- Error-code bars are `red` with the merged `other` bar `muted`. The 3016 donut keeps the shared title block and palette until `chart-pie-donut-rework` lands.

## Using charts from an investigation

Any investigation script follows the same shape:

1. Compute the plotted values in a pure, tested function (counts, rates, ranges); no drawing there.
2. Call one shared `render_*` function with plain lists and a title; it returns PNG `bytes`.
3. The script owns file I/O: save with `write_chart_png(png, output_dir, tenant, filename)` into `output/<TENANT>/charts/` (created on first write), not beside the CSV/XLSX it accompanies.
4. Catch `ChartError`, log it and carry on; a failed chart must never block the CSV, XLSX or text report.

Worked example (story charts): `investigations/shaka-6001/scripts/chart_before_after.py` builds each chart from a pure values helper (`non_webview_counts`, `change_phrase`), computes the finding title
from the values, and hands `RateRow`/`TrendSeries` lists to the renderer. Worked example (composed figure): `investigations/ctap-smvod/scripts/chart_concurrent_playback.py` (pilot, CH-6) composes
`new_figure`, `draw_header`, `style_axes` and `render_png` directly for a three-series line chart, because `render_signed_line` and `render_bar` draw a single series with no header; `write_chart`
shows the `ChartError` handling. Other investigations adopt the layer in their own stories.

A new chart must be a story chart unless it genuinely needs several series or a header strip; in that case use `stacked_bar`/`new_figure` and keep the shared title, palette and rounded bars. Never
copy a renderer into an investigation script: if the shape is missing, add it to `src/lib/charts/` with a happy-path and an error test.

Prototype new chart shapes in `scratch/` first (`SCRATCH.md` convergence rule) and promote into `src/lib/charts/` only once a second investigation needs them. The synchronous render needs no
`asyncio.to_thread`; use it only when a chart is rendered inside an async service.

## Adapting to a new chart type

Reuse the theme, `chart_font_family()`, a shared `style_axes()` and the figure/save recipe above unchanged. Only the data layer and the annotations are new. If a chart genuinely needs a token the
theme lacks (a third semantic colour, say), add it to the theme with a test and a row in the table above in the same commit.

## Provenance

Palette, type scale and recipe come from NiftyShield (`docs/reference/chart_guidelines.md`, reference implementation `src/notifications/payoff_chart*.py` there). NiftyShield-only rules (`₹` money
helpers, Telegram delivery, `RenderError`, `asyncio.to_thread`) were dropped or generalised here.
