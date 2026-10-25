from __future__ import annotations

import pytest
from lib.drm_funnel import FunnelRow
from lib.drm_funnel_charts import ChartSpec, build_chart_specs, render_chart
from lib.funnel_stages_chart import (
    STAGE_NAMES,
    bar_label,
    header_cells,
    left_margin_for_labels,
    render_stages_chart,
    step_labels,
)
from test_drm_funnel_charts import ROWS

from src.lib.charts.errors import ChartError
from src.lib.charts.fig import MARGIN_LEFT
from src.lib.charts.header import Tone
from src.lib.charts.theme import DARK

TOTALS = {"sessions": 1000, "drm_requested": 535, "license_success": 529, "errored": 40}


def test_step_conversion_rates() -> None:
    assert step_labels(TOTALS) == ["-46.5% vs sessions", "98.9% of DRM requested", ""]
    no_requests = {"sessions": 10, "drm_requested": 0, "license_success": 0, "errored": 0}
    assert step_labels(no_requests) == ["-100% vs sessions", "no DRM requests", ""]
    assert bar_label(529, 1000) == "529 · 52.9% of sessions"


def test_header_has_error_rate_in_negative_tone() -> None:
    rate, sessions = header_cells(TOTALS)
    assert (rate.value, rate.tone) == ("4%", Tone.NEGATIVE)
    assert sessions.value == "1k"


def test_left_margin_fits_longest_label() -> None:
    assert left_margin_for_labels(["a"]) == MARGIN_LEFT
    wide = left_margin_for_labels(STAGE_NAMES)
    assert wide > left_margin_for_labels(["Sessions"])
    assert left_margin_for_labels(["x" * 200]) <= 0.45


def test_stages_chart_returns_png() -> None:
    assert render_stages_chart(TOTALS, title="t", subtitle="s").startswith(b"\x89PNG")
    spec = next(s for s in build_chart_specs("ZA", "2026-10-23", ROWS) if s.name == "stages")
    assert isinstance(spec, ChartSpec) and render_chart(spec).startswith(b"\x89PNG")


def test_zero_sessions_raises_chart_error() -> None:
    with pytest.raises(ChartError):
        render_stages_chart({**TOTALS, "sessions": 0}, title="t")
    with pytest.raises(ChartError):
        render_stages_chart({"sessions": 5}, title="t")


def test_error_codes_chart_is_red_with_muted_other_and_header() -> None:
    from lib.drm_funnel_charts import error_bar_colours

    assert error_bar_colours(["6001", "other"]) == [DARK.red, DARK.muted]
    rows = [*ROWS, FunnelRow("ZA", "2026-10-23", "merge", "vod", "widevine", "failed", "3016", 4, error_code="3016")]
    spec = next(s for s in build_chart_specs("ZA", "2026-10-23", rows) if s.name == "error_codes")
    assert spec.header and spec.header[0].tone is Tone.NEGATIVE
    assert render_chart(spec).startswith(b"\x89PNG")
