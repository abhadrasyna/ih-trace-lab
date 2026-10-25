"""DRM funnel ``stages`` chart: horizontal funnel bars coloured by meaning, step conversion, error-rate header.

Pure helpers (margin, conversion, labels) do no drawing; ``render_stages_chart`` returns PNG bytes or raises ``ChartError``.
Investigation-local; promote to ``src/lib/charts/`` only if a second investigation needs it.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

from src.lib.charts.axes import format_count, format_pct, style_axes
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import BASE_WIDTH, MARGIN_LEFT, MARGIN_RIGHT, TWO_ROW_HEIGHT, new_figure, render_png
from src.lib.charts.header import HeaderCell, Tone, draw_header
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.charts.title import draw_title

STAGE_KEYS = ("sessions", "drm_requested", "license_success", "errored")
STAGE_NAMES = ("Sessions", "DRM requested", "License success", "Ended in error")
# Colour by meaning: neutral series colour for volume stages, green for success, red for error.
STAGE_COLOURS = (None, None, "green", "red")
TICK_FONT_SIZE = 9.0
CHAR_WIDTH_PER_PT_IN = 0.0085  # same rough advance as the header packer
LABEL_PAD_IN = 0.25
MAX_MARGIN_LEFT = 0.45
BAR_HEIGHT = 0.55
HEADER_Y_SHIFT = 0.095  # header sits under the title block
AXES_TOP = 0.76
RIGHT_HEADROOM = 1.55  # x-limit multiple of the longest bar so end labels never clip


def left_margin_for_labels(labels: Sequence[str], font_size: float = TICK_FONT_SIZE) -> float:
    """Figure-fraction left margin wide enough for the longest label, never below ``MARGIN_LEFT``."""
    longest = max((len(label) for label in labels), default=0)
    needed_in = longest * font_size * CHAR_WIDTH_PER_PT_IN + LABEL_PAD_IN
    return min(MAX_MARGIN_LEFT, max(MARGIN_LEFT, needed_in / BASE_WIDTH))


def stage_counts(totals: Mapping[str, int]) -> list[int]:
    return [totals[k] for k in STAGE_KEYS]


def step_labels(totals: Mapping[str, int]) -> list[str]:
    """Annotation for the gap after each of the first three bars (``""`` where none applies).

    Sessions -> DRM requested is a change against sessions; DRM requested -> License success is a share of
    DRM requested, so the base is named in the text. Both use the same numbers as ``stage_totals``.
    """
    sessions, requested, success = totals["sessions"], totals["drm_requested"], totals["license_success"]
    drop = 100 * (requested - sessions) / sessions
    conv = f"{format_pct(round(100 * success / requested, 1))} of DRM requested" if requested else "no DRM requests"
    return [f"{format_pct(round(drop, 1))} vs sessions", conv, ""]


def bar_label(count: int, sessions: int) -> str:
    """End-of-bar label: the count and its share of all sessions (the base is stated on the chart)."""
    return f"{format_count(count)} · {format_pct(round(100 * count / sessions, 1))} of sessions"


def header_cells(totals: Mapping[str, int]) -> list[HeaderCell]:
    rate = 100 * totals["errored"] / totals["sessions"]
    return [
        HeaderCell("ERROR RATE", format_pct(round(rate, 1)), Tone.NEGATIVE),
        HeaderCell("SESSIONS", format_count(totals["sessions"])),
    ]


def _require_totals(totals: Mapping[str, int]) -> None:
    if any(k not in totals for k in STAGE_KEYS):
        raise ChartError(f"stage totals need keys {STAGE_KEYS}")
    if totals["sessions"] <= 0:
        raise ChartError("no sessions to chart")


def render_stages_chart(totals: Mapping[str, int], *, title: str, subtitle: str = "",
                        theme: ChartTheme = DARK) -> bytes:
    """Renders the funnel stages chart to PNG bytes; raises ``ChartError`` on bad input or any drawing failure."""
    _require_totals(totals)
    counts = stage_counts(totals)
    try:
        family = chart_font_family()
        fig = new_figure(theme, TWO_ROW_HEIGHT)
        fig.subplots_adjust(left=left_margin_for_labels(STAGE_NAMES), right=MARGIN_RIGHT, top=AXES_TOP)
        draw_title(fig, title, subtitle, theme, family)
        draw_header(fig, header_cells(totals), theme, family, y_shift=HEADER_Y_SHIFT)
        ax = fig.add_subplot(111)
        longest = max(counts)
        colours = [getattr(theme, c) if c else theme.series[0] for c in STAGE_COLOURS]
        ys = list(range(len(counts)))
        ax.barh(ys, counts, color=colours, height=BAR_HEIGHT)
        for y, count in zip(ys, counts, strict=True):
            ax.annotate(bar_label(count, totals["sessions"]), xy=(count, y), xytext=(5, 0),
                        textcoords="offset points", ha="left", va="center", color=theme.ink, fontsize=8.5,
                        fontweight="bold", family=family)
        for y, text in zip(ys, step_labels(totals), strict=False):
            if text:
                ax.text(0, y + 0.5, text, ha="left", va="center", color=theme.muted, fontsize=8, family=family)
        ax.set_yticks(ys, list(STAGE_NAMES))
        ax.invert_yaxis()
        ax.set_xlim(0, longest * RIGHT_HEADROOM)
        style_axes(ax, theme, family)
        ax.xaxis.set_major_formatter(lambda v, _pos: format_count(v))
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color=theme.faint, lw=0.6)
        return render_png(fig, theme)
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"stages chart failed: {exc}") from exc
