from __future__ import annotations

import csv
from pathlib import Path

from conftest import load_script
from lib.drm_funnel import FunnelRow, stage_totals
from lib.drm_funnel_charts import (
    build_chart_specs,
    drm_split_series,
    drm_type_colour,
    drm_type_label,
    error_code_series,
    license_outcome_series,
    ordered_drm_types,
    outcome_colours,
    render_chart,
    stage_series,
    subcategory_series,
)
from test_analyze_drm_funnel import _inputs

from src.lib.charts.errors import ChartError
from src.lib.charts.theme import DARK

cli = load_script("analyze_drm_funnel.py")


def _row(source, kind, bucket, outcome, err, n) -> FunnelRow:
    return FunnelRow("ZA", "2026-10-23", source, kind, bucket, outcome, err, n)


ROWS = [
    _row("merge", "vod", "widevine", "success", "none", 5),
    _row("merge", "vod", "widevine", "failed", "3016", 2),
    _row("merge", "linear", "fairplay", "retry_then_success", "6xxx", 1),
    _row("drm_only", "vod", "widevine", "failed", "none", 1),
    _row("merge", "vod", "no_drm_activity", "no_request", "3016", 3),
]
TOTAL = sum(r.sessions for r in ROWS)


def test_series_builders_reconcile_to_session_total() -> None:
    _, stages = stage_series(ROWS)
    assert stages["sessions"][0] == TOTAL
    assert stages["sessions"] == [TOTAL, stage_totals(ROWS)["drm_requested"], 6, 6]
    _, split = drm_split_series(ROWS)
    assert sum(sum(v) for v in split.values()) == TOTAL
    labels, outcome = license_outcome_series(ROWS)
    assert sum(sum(v) for v in outcome.values()) == TOTAL
    assert all(len(v) == len(labels) for v in outcome.values())
    assert list(outcome) == ["success", "failed", "no_request"]
    assert outcome_colours(outcome) == {"success": "green", "failed": "red", "no_request": "muted"}
    assert [s.name for s in build_chart_specs("ZA", "2026-10-23", ROWS)] == ["stages", "drm_split", "license_outcome"]


def test_drm_type_order_is_stable_across_charts() -> None:
    rows = [_row("merge", "vod", b, "success", "none", n)
            for b, n in (("no_drm_activity", 9), ("playready", 1), ("fairplay", 5), ("widevine", 3))]
    expected = ["Widevine", "Fairplay", "Playready", "No DRM activity"]
    assert ordered_drm_types(rows) == ["widevine", "fairplay", "playready", "no_drm_activity"]
    assert drm_split_series(rows)[0] == expected
    assert license_outcome_series(rows)[0] == expected
    assert drm_type_colour("widevine") != drm_type_colour("fairplay")
    assert drm_type_colour("no_drm_activity") == DARK.muted


def test_unknown_bucket_sorts_last() -> None:
    rows = [_row("merge", "vod", b, "success", "none", 1) for b in ("zzz", "no_drm_activity", "aaa", "widevine")]
    assert ordered_drm_types(rows) == ["widevine", "no_drm_activity", "aaa", "zzz"]
    assert drm_type_colour("aaa") == DARK.muted
    assert drm_type_label("aaa") == "Aaa"
    labels, series = drm_split_series(rows)
    assert labels[-1] == "Zzz" and sum(sum(v) for v in series.values()) == 4


def test_drm_split_spec_mutes_none_and_keeps_one_colour_per_type() -> None:
    spec = next(s for s in build_chart_specs("ZA", "2026-10-23", ROWS) if s.name == "drm_split")
    assert spec.labels == ["Widevine", "Fairplay", "No DRM activity"] and list(spec.series) == ["linear", "vod"]
    assert spec.bar_colours is None
    vod_only = [r for r in ROWS if r.kind == "vod"]
    spec = next(s for s in build_chart_specs("ZA", "2026-10-23", vod_only) if s.name == "drm_split")
    assert spec.bar_colours == [drm_type_colour("widevine"), DARK.muted]
    assert render_chart(spec).startswith(b"\x89PNG")


def test_license_outcome_spec_is_share_by_default_and_absolute_on_request() -> None:
    spec = next(s for s in build_chart_specs("ZA", "2026-10-23", ROWS) if s.name == "license_outcome")
    assert spec.normalize and spec.legend == "above" and spec.total is None
    assert spec.labels == ["Widevine\n8", "Fairplay\n1", "No DRM activity\n3"]
    assert "share of each DRM type" in spec.subtitle
    assert render_chart(spec).startswith(b"\x89PNG")
    raw = next(s for s in build_chart_specs("ZA", "2026-10-23", ROWS, absolute=True) if s.name == "license_outcome")
    assert not raw.normalize and raw.labels == ["Widevine", "Fairplay", "No DRM activity"] and raw.total == TOTAL
    assert render_chart(raw).startswith(b"\x89PNG")


def test_error_mix_series_reconcile_to_errored_sessions() -> None:
    codes = ["6001"] * 1 + ["1003", "1004", "1005", "1006", "1007", "1008", "3016"]
    rows = [FunnelRow("ZA", "2026-10-23", "merge", "vod", "widevine", "success", "x", n, c,
                      "Video decode error" if c == "3016" else "")
            for n, c in zip([50, 9, 8, 7, 6, 5, 4, 3], codes, strict=True)]
    rows.append(_row("merge", "vod", "widevine", "success", "none", 100))
    labels, series = error_code_series(rows)
    assert labels[0] == "6001" and labels[-1] == "other" and len(labels) == 6
    assert sum(series["sessions"]) == 92
    sub_labels, sub = subcategory_series(rows)
    assert sub_labels == ["Video decode error"] and sub["sessions"] == [3]
    names = [s.name for s in build_chart_specs("ZA", "2026-10-23", rows)]
    assert names[-2:] == ["error_codes", "3016_subcategory"]


def test_no_errors_yields_empty_error_mix_and_no_extra_charts() -> None:
    assert error_code_series(ROWS) == ([], {"sessions": []})
    assert subcategory_series([_row("merge", "vod", "widevine", "success", "none", 1)])[0] == []
    blank = [FunnelRow("ZA", "2026-10-23", "merge", "vod", "widevine", "success", "x", 2, "3016")]
    assert subcategory_series(blank) == (["unclassified"], {"sessions": [2]})


def test_markdown_embeds_relative_chart_links(tmp_path: Path) -> None:
    base, drm = _inputs(tmp_path)
    cli.run("ZA", "2026-10-23", base, drm)
    md = (base / "ZA" / "drm-analysis" / "2026-10-23_drm_funnel.md").read_text()
    for name in ("stages", "drm_split", "license_outcome"):
        png = base / "ZA" / "drm-analysis" / "charts" / f"2026-10-23_drm_funnel_{name}.png"
        assert png.read_bytes().startswith(b"\x89PNG")
        assert f"(charts/2026-10-23_drm_funnel_{name}.png)" in md


def test_chart_error_still_writes_csv_and_markdown_without_image_links(tmp_path: Path, monkeypatch) -> None:
    def boom(spec):
        raise ChartError("no font")

    monkeypatch.setattr(cli, "render_chart", boom)
    base, drm = _inputs(tmp_path)
    cli.run("ZA", "2026-10-23", base, drm)
    md = (base / "ZA" / "drm-analysis" / "2026-10-23_drm_funnel.md").read_text()
    assert "charts/" not in md and "## Stages" in md
    rows = list(csv.DictReader((base / "ZA" / "drm-analysis" / "csv" / "2026-10-23_drm_funnel.csv").open()))
    assert sum(int(r["sessions"]) for r in rows) == 4
    assert not (base / "ZA" / "drm-analysis" / "charts").exists()
