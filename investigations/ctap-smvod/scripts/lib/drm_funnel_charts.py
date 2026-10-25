"""DRM funnel charts: pure series builders over ``FunnelRow`` plus thin ``render_stacked_bar`` wrappers.

Builders do no I/O and no drawing; ``render_*`` return PNG bytes or raise ``ChartError``.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.drm_funnel import (
    FAILED,
    NAMED_ERRORS,
    NO_ERROR,
    NO_REQUEST,
    RETRY_THEN_SUCCESS,
    SUCCESS,
    FunnelRow,
    stage_totals,
)
from lib.funnel_stages_chart import header_cells, render_stages_chart

from src.lib.charts.axes import format_count
from src.lib.charts.header import HeaderCell
from src.lib.charts.pie import OTHER_LABEL, merge_small_slices, render_pie
from src.lib.charts.stacked_bar import render_stacked_bar
from src.lib.charts.theme import DARK, ChartTheme

STAGE_NAMES = ("Sessions", "DRM requested", "License success", "Ended in error")
# The three semantic outcome series; the downstream-error split lives in the markdown tables, not in colour.
OUTCOME_GROUPS = (
    ("success", (SUCCESS, RETRY_THEN_SUCCESS)),
    ("failed", (FAILED,)),
    ("no_request", (NO_REQUEST,)),
)
OUTCOME_COLOURS = {"success": "green", "failed": "red", "no_request": "muted"}
# Fixed order: a DRM type keeps its position and colour (series index) in every chart; ``no_drm_activity`` is muted.
DRM_TYPE_ORDER = ("widevine", "fairplay", "playready", "no_drm_activity")
UNKNOWN_DRM_RANK = len(DRM_TYPE_ORDER)
TOP_ERROR_CODES = 6  # top 5 codes plus "other"


@dataclass(frozen=True)
class ChartSpec:
    """Inputs for one ``render_stacked_bar`` call, built from funnel rows."""

    name: str
    title: str
    subtitle: str
    labels: list[str]
    series: dict[str, list[int]]
    colours: dict[str, str] = field(default_factory=dict)
    horizontal: bool = False
    total: int | None = None
    pie: bool = False
    bar_colours: list[str] | None = None
    normalize: bool = False
    legend: str = "auto"
    stage_totals: dict[str, int] | None = None
    header: list[HeaderCell] | None = None

def ordered_drm_types(rows: Sequence[FunnelRow]) -> list[str]:
    """DRM buckets present in ``rows`` in the fixed funnel order; unknown buckets sort last, alphabetically."""
    present = {r.drm_bucket for r in rows}
    return sorted(present, key=lambda b: (DRM_TYPE_ORDER.index(b) if b in DRM_TYPE_ORDER else UNKNOWN_DRM_RANK, b))


def drm_type_label(bucket: str) -> str:
    """Display label for a DRM bucket (``widevine -> Widevine``, ``no_drm_activity -> No DRM activity``)."""
    if bucket == "no_drm_activity":
        return "No DRM activity"
    return bucket.capitalize()


def drm_type_colour(bucket: str, theme: ChartTheme = DARK) -> str:
    """Fixed colour per DRM type: the series palette by order index; ``no_drm_activity`` and unknown buckets are muted."""
    if bucket in DRM_TYPE_ORDER and bucket != "no_drm_activity" and DRM_TYPE_ORDER.index(bucket) < len(theme.series):
        return theme.series[DRM_TYPE_ORDER.index(bucket)]
    return theme.muted


def stage_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    t = stage_totals(rows)
    counts = [t["sessions"], t["drm_requested"], t["license_success"], t["errored"]]
    return list(STAGE_NAMES), {"sessions": counts}


def drm_split_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    """Sessions per DRM bucket, stacked by VOD/linear kind."""
    cells: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cells[r.drm_bucket][r.kind] += r.sessions
    buckets = ordered_drm_types(rows)
    kinds = sorted({k for per in cells.values() for k in per})
    return [drm_type_label(b) for b in buckets], {k: [cells[b][k] for b in buckets] for k in kinds}


def license_outcome_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    """Per DRM bucket: sessions by license outcome (success / failed / no_request); absent outcomes are omitted."""
    buckets = ordered_drm_types(rows)
    series: dict[str, list[int]] = {}
    for group, outcomes in OUTCOME_GROUPS:
        counts = [sum(r.sessions for r in rows if r.drm_bucket == b and r.license_outcome in outcomes)
                  for b in buckets]
        if any(counts):
            series[group] = counts
    return [drm_type_label(b) for b in buckets], series


def labels_with_totals(labels: Sequence[str], series: dict[str, list[int]]) -> list[str]:
    """Adds each stack's absolute total on a second line under its label (``Widevine`` -> ``Widevine`` / ``1.2k``)."""
    return [f"{label}\n{format_count(sum(v[i] for v in series.values()))}" for i, label in enumerate(labels)]


def error_code_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    """Errored sessions by exact first error code: the top 5 plus ``other``."""
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.error_code != NO_ERROR:
            counts[r.error_code] += r.sessions
    if not counts:
        return [], {"sessions": []}
    labels, values = merge_small_slices(list(counts), list(counts.values()), TOP_ERROR_CODES)
    return labels, {"sessions": values}


def subcategory_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    """3014/3015/3016 sessions by triage sub-category."""
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.error_code in NAMED_ERRORS:
            counts[r.subcategory or "unclassified"] += r.sessions
    labels = sorted(counts, key=lambda k: (-counts[k], k))
    return labels, {"sessions": [counts[k] for k in labels]}


def outcome_colours(series: dict[str, list[int]]) -> dict[str, str]:
    """Success green, failed red, no_request muted."""
    return {n: OUTCOME_COLOURS[n] for n in series if n in OUTCOME_COLOURS}


def error_bar_colours(labels: Sequence[str]) -> list[str]:
    """Error codes are errors, so red like the stages chart's error bar; the merged ``other`` bar is muted."""
    return [DARK.muted if label == OTHER_LABEL else DARK.red for label in labels]


def split_bar_colours(rows: Sequence[FunnelRow], series: dict[str, list[int]]) -> list[str] | None:
    """Per-bar DRM colours when one series (a single kind) is drawn; stacked kinds use the legend palette."""
    if len(series) != 1:
        return None
    return [drm_type_colour(b) for b in ordered_drm_types(rows)]


def build_chart_specs(opco: str, date: str, rows: Sequence[FunnelRow], *, absolute: bool = False) -> list[ChartSpec]:
    """Specs for every funnel chart; ``absolute`` draws ``license_outcome`` as raw counts instead of shares."""
    t = stage_totals(rows)
    sub = f"{opco} {date} · {t['sessions']} sessions · {t['drm_only']} drm_only"
    stage_labels, stage_s = stage_series(rows)
    split_labels, split_s = drm_split_series(rows)
    out_labels, out_s = license_outcome_series(rows)
    err_labels, err_s = error_code_series(rows)
    sub_labels, sub_s = subcategory_series(rows)
    specs = [
        ChartSpec("stages", "DRM funnel stages", sub, stage_labels, stage_s, horizontal=True,
                  total=t["sessions"], stage_totals=t),
        ChartSpec("drm_split", "Sessions by DRM type", sub, split_labels, split_s, total=t["sessions"],
                  bar_colours=split_bar_colours(rows, split_s)),
        ChartSpec("license_outcome", "License outcome per DRM type",
                  sub if absolute else f"{sub} · share of each DRM type's sessions",
                  out_labels if absolute else labels_with_totals(out_labels, out_s), out_s,
                  colours=outcome_colours(out_s), total=t["sessions"] if absolute else None,
                  normalize=not absolute, legend="above"),
    ]
    # Error-mix charts only exist when there is something to plot.
    if err_labels:
        # A bar, not a pie: one code (6001) usually dominates and a pie would hide the rest.
        specs.append(ChartSpec("error_codes", "Errored sessions by first error code", sub, err_labels, err_s,
                               horizontal=True, total=t["errored"], bar_colours=error_bar_colours(err_labels),
                               header=header_cells(t)))
    if sub_labels:
        specs.append(ChartSpec("3016_subcategory", "3014/3015/3016 by sub-category", sub, sub_labels, sub_s,
                               pie=True))
    return specs


def render_chart(spec: ChartSpec) -> bytes:
    if spec.stage_totals is not None:
        return render_stages_chart(spec.stage_totals, title=spec.title, subtitle=spec.subtitle)
    if spec.pie:
        return render_pie(spec.labels, spec.series["sessions"], title=spec.title, subtitle=spec.subtitle)
    return render_stacked_bar(
        spec.labels, spec.series, title=spec.title, subtitle=spec.subtitle,
        horizontal=spec.horizontal, colours=spec.colours or None, bar_colours=spec.bar_colours, total=spec.total,
        normalize=spec.normalize, legend=spec.legend, header=spec.header,
    )


def chart_filename(date: str, name: str) -> str:
    return f"{date}_drm_funnel_{name}.png"
