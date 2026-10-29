"""Tests for the bandwidth-vs-failure runner, stats library, analysis tables and charts (offline)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import load_script
from src.lib.charts.errors import ChartError

stats = load_script("lib/bandwidth_stats.py")
runner = load_script("run_athena_session_bandwidth.py")
analyze = load_script("analyze_bandwidth_vs_failure.py")
chart = load_script("chart_bandwidth_vs_failure.py")


def row(code: str = "", bw: str = "", buffering: str = "0", abr: str = "", stream: str = "", etype: str = "") -> dict[str, str]:
    return {
        "sessionid": "s", "has_error": "true" if code else "false", "first_errorcode": code, "est_bw_mbps_max": bw,
        "stream_bw_mbps": stream, "buffering_events": buffering, "buf_cur_last": "0", "abr_bitrate_mbps_avg": abr, "nav_effectivetype": etype,
    }


def test_percentile_interpolates_and_rejects_bad_q():
    assert stats.percentile([1, 2, 3, 4, 5], 50) == 3
    assert stats.percentile([], 50) is None
    with pytest.raises(ValueError):
        stats.percentile([1], 101)


def test_spearman_perfect_inverse_and_too_few_points():
    assert stats.spearman([1, 2, 3, 4, 5], [10, 8, 6, 4, 2]) == pytest.approx(-1.0)
    assert stats.spearman([1, 2], [2, 1]) is None
    assert stats.spearman([1, 1, 1, 1, 1], [1, 2, 3, 4, 5]) is None


def test_mann_whitney_detects_shift_and_needs_min_n():
    result = stats.mann_whitney([1, 2, 3, 4, 5, 6], [10, 11, 12, 13, 14, 15])
    assert result["p_value"] < 0.05 and result["prob_a_lower"] == pytest.approx(1.0)
    assert stats.mann_whitney([1, 2], [3, 4]) is None


def test_num_and_is_true_fail_loudly_on_bad_values():
    assert stats.num("") is None and stats.num("1.5") == 1.5
    with pytest.raises(ValueError):
        stats.num("abc")
    with pytest.raises(ValueError):
        stats.is_true("maybe")


def test_summarize_code_handles_no_bandwidth():
    out = stats.summarize_code([row("6001"), row("6001")])
    assert out["sessions"] == 2 and out["with_bandwidth"] == 0 and out["bw_p50"] is None and out["spearman_bw_vs_buffering"] is None


def test_failure_rate_by_abr_bucket_counts_errors():
    rows = [row("3016", abr="0.5"), row("", abr="0.6"), row("", abr="7")]
    table = {r["abr_bucket_mbps"]: r for r in stats.failure_rate_by_abr_bucket(rows)}
    assert table["<1"]["error_rate_pct"] == 50.0 and table[">=6"]["error_rate_pct"] == 0.0
    assert table["1-3"]["error_rate_pct"] is None


def test_by_errorcode_table_appends_healthy_baseline():
    rows = [row("3016", bw="2.0", buffering="4"), row("", buffering="10")]
    table = analyze.by_errorcode_table(rows)
    assert [t["errorcode"] for t in table] == ["3016", "(healthy baseline)"]
    assert table[1]["avg_buffering_events"] == 10


def test_effectivetype_table_labels_blank_as_unknown():
    table = analyze.effectivetype_table([row("1003", etype="4g"), row("1003")])
    assert {t["effectivetype"] for t in table} == {"4g", "unknown"}


def test_read_rows_rejects_missing_columns(tmp_path):
    bad = tmp_path / "x.csv"
    bad.write_text("sessionid,has_error\ns,true\n")
    with pytest.raises(ValueError):
        analyze.read_rows(bad)


def test_build_query_renders_one_utc_day():
    sql = runner.build_query(SimpleNamespace(debug_events_table="e6auj7k7_ccl_debug_events"), "unified_e6auj7k7", "2026-10-24")
    assert "2026-10-24T00:00:00.000Z" in sql and "2026-10-25T00:00:00.000Z" in sql and "{{" not in sql


def test_render_charts_return_png_and_fail_with_chart_error():
    rows = [row("3016", bw=str(0.5 + i), buffering=str(i % 4), abr="2") for i in range(8)] + [row("", buffering="3", abr="1.5") for _ in range(6)]
    for _, render in chart.CHARTS:
        assert render(rows, "t")[:8] == b"\x89PNG\r\n\x1a\n"
    with pytest.raises(ChartError):
        chart.render_spread([row("6001")], "t")
