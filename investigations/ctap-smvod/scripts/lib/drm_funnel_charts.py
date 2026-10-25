"""DRM funnel charts: pure series builders over ``FunnelRow`` plus thin ``render_stacked_bar`` wrappers.

Builders do no I/O and no drawing; ``render_*`` return PNG bytes or raise ``ChartError``.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.drm_funnel import (
    FAILED, NO_ERROR, NO_REQUEST, RETRY_THEN_SUCCESS, SUCCESS, FunnelRow, stage_totals,
)
from src.lib.charts.stacked_bar import render_stacked_bar

STAGE_NAMES = ("Sessions", "DRM requested", "License success", "Ended in error")
# Error splits per outcome group; kept to 7 series at most so palette colours never repeat.
OUTCOME_GROUPS = (
    ("success", (SUCCESS, RETRY_THEN_SUCCESS), ("", "error")),
    ("failed", (FAILED,), ("", "error")),
    ("no_request", (NO_REQUEST,), ("", "3016", "other error")),
)
OUTCOME_COLOURS = {"success": "green", "failed": "red", "no_request": "muted"}
CHART_NAMES = ("stages", "drm_split", "license_outcome")


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
    labels = sorted(cells, key=lambda b: -sum(cells[b].values()))
    kinds = sorted({k for per in cells.values() for k in per})
    return labels, {k: [cells[b][k] for b in labels] for k in kinds}


def license_outcome_series(rows: Sequence[FunnelRow]) -> tuple[list[str], dict[str, list[int]]]:
    """Per DRM bucket: success / failed / no_request split by downstream error (no_request: 3016 vs other)."""
    labels = sorted({r.drm_bucket for r in rows})
    cells: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    order: list[str] = []
    for group, outcomes, splits in OUTCOME_GROUPS:
        for suffix in splits:
            name = f"{group}, {suffix}" if suffix else group
            order.append(name)
            for r in rows:
                if r.license_outcome in outcomes and _split_class(_error_class(r.error_group), splits) == suffix:
                    cells[name][r.drm_bucket] += r.sessions
    series = {n: [cells[n][b] for b in labels] for n in order if any(cells[n].values())}
    return labels, series


def outcome_colours(series: dict[str, list[int]]) -> dict[str, str]:
    """Plain outcome series use success green / failure red; error-split series fall back to the palette."""
    return {n: OUTCOME_COLOURS[n] for n in series if n in OUTCOME_COLOURS}


def build_chart_specs(opco: str, date: str, rows: Sequence[FunnelRow]) -> list[ChartSpec]:
    t = stage_totals(rows)
    sub = f"{opco} {date} · {t['sessions']} sessions · {t['drm_only']} drm_only"
    stage_labels, stage_s = stage_series(rows)
    split_labels, split_s = drm_split_series(rows)
    out_labels, out_s = license_outcome_series(rows)
    return [
        ChartSpec("stages", "DRM funnel stages", sub, stage_labels, stage_s, horizontal=True,
                  total=t["sessions"]),
        ChartSpec("drm_split", "Sessions by DRM type", sub, split_labels, split_s, total=t["sessions"]),
        ChartSpec("license_outcome", "License outcome per DRM type", sub, out_labels, out_s,
                  colours=outcome_colours(out_s), total=t["sessions"]),
    ]


def render_chart(spec: ChartSpec) -> bytes:
    return render_stacked_bar(
        spec.labels, spec.series, title=spec.title, subtitle=spec.subtitle,
        horizontal=spec.horizontal, colours=spec.colours or None, total=spec.total,
    )


def chart_filename(date: str, name: str) -> str:
    return f"{date}_drm_funnel_{name}.png"
