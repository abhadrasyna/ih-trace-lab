"""DRM funnel charts: pure series builders over ``FunnelRow`` plus thin ``render_stacked_bar`` wrappers.

Builders do no I/O and no drawing; ``render_*`` return PNG bytes or raise ``ChartError``.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.drm_funnel import (
    FAILED, NAMED_ERRORS, NO_ERROR, NO_REQUEST, RETRY_THEN_SUCCESS, SUCCESS, FunnelRow, stage_totals,
)
from src.lib.charts.pie import merge_small_slices, render_pie
from src.lib.charts.stacked_bar import render_stacked_bar
from src.lib.charts.theme import DARK, ChartTheme

STAGE_NAMES = ("Sessions", "DRM requested", "License success", "Ended in error")
# Error splits per outcome group; kept to 7 series at most so palette colours never repeat.
OUTCOME_GROUPS = (
    ("success", (SUCCESS, RETRY_THEN_SUCCESS), ("", "error")),
    ("failed", (FAILED,), ("", "error")),
    ("no_request", (NO_REQUEST,), ("", "3016", "other error")),
)
OUTCOME_COLOURS = {"success": "green", "failed": "red", "no_request": "muted"}
# Fixed order: a DRM type keeps its position and colour (series index) in every chart; ``none`` is muted.
DRM_TYPE_ORDER = ("widevine", "fairplay", "playready", "none")
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


def ordered_drm_types(rows: Sequence[FunnelRow]) -> list[str]:
    """DRM buckets present in ``rows`` in the fixed funnel order; unknown buckets sort last, alphabetically."""
    present = {r.drm_bucket for r in rows}
    return sorted(present, key=lambda b: (DRM_TYPE_ORDER.index(b) if b in DRM_TYPE_ORDER else UNKNOWN_DRM_RANK, b))


def drm_type_label(bucket: str) -> str:
    """Display label for a DRM bucket (``widevine -> Widevine``)."""
    return bucket.capitalize()


def drm_type_colour(bucket: str, theme: ChartTheme = DARK) -> str:
    """Fixed colour per DRM type: the series palette by order index; ``none`` and unknown buckets are muted."""
    if bucket in DRM_TYPE_ORDER and bucket != "none" and DRM_TYPE_ORDER.index(bucket) < len(theme.series):
        return theme.series[DRM_TYPE_ORDER.index(bucket)]
    return theme.muted


def _error_class(group: str) -> str:
    if group == NO_ERROR:
        return ""
    return "3016" if group == "3016" else "other error"


def _split_class(error_class: str, splits: Sequence[str]) -> str:
    """Maps an error class onto the group's splits; groups without a 3016 split fold it into ``error``."""
    return error_class if error_class in splits else ("error" if error_class else "")


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
    """Per DRM bucket: success / failed / no_request split by downstream error (no_request: 3016 vs other)."""
    buckets = ordered_drm_types(rows)
    cells: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    order: list[str] = []
    for group, outcomes, splits in OUTCOME_GROUPS:
        for suffix in splits:
            name = f"{group}, {suffix}" if suffix else group
            order.append(name)
            for r in rows:
                if r.license_outcome in outcomes and _split_class(_error_class(r.error_group), splits) == suffix:
                    cells[name][r.drm_bucket] += r.sessions
    series = {n: [cells[n][b] for b in buckets] for n in order if any(cells[n].values())}
    return [drm_type_label(b) for b in buckets], series


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
    """Plain outcome series use success green / failure red; error-split series fall back to the palette."""
    return {n: OUTCOME_COLOURS[n] for n in series if n in OUTCOME_COLOURS}


def build_chart_specs(opco: str, date: str, rows: Sequence[FunnelRow]) -> list[ChartSpec]:
    t = stage_totals(rows)
    sub = f"{opco} {date} · {t['sessions']} sessions · {t['drm_only']} drm_only"
    stage_labels, stage_s = stage_series(rows)
    split_labels, split_s = drm_split_series(rows)
    out_labels, out_s = license_outcome_series(rows)
    err_labels, err_s = error_code_series(rows)
    sub_labels, sub_s = subcategory_series(rows)
    specs = [
        ChartSpec("stages", "DRM funnel stages", sub, stage_labels, stage_s, horizontal=True,
                  total=t["sessions"]),
        ChartSpec("drm_split", "Sessions by DRM type", sub, split_labels, split_s, total=t["sessions"]),
        ChartSpec("license_outcome", "License outcome per DRM type", sub, out_labels, out_s,
                  colours=outcome_colours(out_s), total=t["sessions"]),
    ]
    # Error-mix charts only exist when there is something to plot.
    if err_labels:
        # A bar, not a pie: one code (6001) usually dominates and a pie would hide the rest.
        specs.append(ChartSpec("error_codes", "Errored sessions by first error code", sub, err_labels, err_s,
                               horizontal=True, total=t["errored"]))
    if sub_labels:
        specs.append(ChartSpec("3016_subcategory", "3014/3015/3016 by sub-category", sub, sub_labels, sub_s,
                               pie=True))
    return specs


def render_chart(spec: ChartSpec) -> bytes:
    if spec.pie:
        return render_pie(spec.labels, spec.series["sessions"], title=spec.title, subtitle=spec.subtitle)
    return render_stacked_bar(
        spec.labels, spec.series, title=spec.title, subtitle=spec.subtitle,
        horizontal=spec.horizontal, colours=spec.colours or None, total=spec.total,
    )


def chart_filename(date: str, name: str) -> str:
    return f"{date}_drm_funnel_{name}.png"
