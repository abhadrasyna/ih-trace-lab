from __future__ import annotations

import csv
import json
from pathlib import Path

import openpyxl
import pytest

from .conftest import load_script

analyze_api_timing = load_script("analyze_api_timing.py")
analyze_errorcode_correlation = load_script("analyze_errorcode_correlation.py")
analyze_outcome_report = load_script("analyze_outcome_report.py")
analyze_session_guard_net_latency = load_script("analyze_session_guard_net_latency.py")
analyze_webview_devices = load_script("analyze_webview_devices.py")
analyze_wv_device_cross_date_success = load_script("analyze_wv_device_cross_date_success.py")
analyze_wv_failure_then_success_devices = load_script("analyze_wv_failure_then_success_devices.py")
parse_debug_user_agents = load_script("parse_debug_user_agents.py")


def test_analyze_api_timing_phase_breakdown_computes_segments() -> None:
    row = {
        "dns_resolved_seconds": 0.1,
        "tcp_connected_seconds": 0.3,
        "tls_done_seconds": 0.5,
        "request_sent_seconds": 0.6,
        "first_byte_seconds": 1.0,
        "response_complete_seconds": 1.4,
    }

    assert analyze_api_timing.phase_breakdown(row) == (0.1, 0.19999999999999998, 0.2, 0.4, 0.3999999999999999)


def test_analyze_api_timing_load_rows_coerces_numeric_cells(tmp_path: Path) -> None:
    xlsx = tmp_path / "api.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "in"
    ws.append(["record_type", "step", "total_time_seconds", "dns_resolved_seconds", "tcp_connected_seconds", "tls_done_seconds", "request_sent_seconds", "first_byte_seconds", "response_complete_seconds", "redirect_time_seconds"])
    ws.append(["api", "manifest", 1.5, 0.1, 0.2, 0.3, 0.4, 0.9, 1.5, None])
    wb.save(xlsx)

    rows = analyze_api_timing.load_rows(str(xlsx))

    assert rows[0]["total_time_seconds"] == 1.5
    assert rows[0]["redirect_time_seconds"] is None


def test_analyze_errorcode_correlation_loads_lookup_and_parses_rows(tmp_path: Path) -> None:
    output = tmp_path / "2026-09-30_setupsession_with_outcome.csv"
    output.write_text("sessionId,householdId,deviceId,contentId,externalPackageId\ns1,hh1,d1,c1,p1\n", encoding="utf-8")
    errors = tmp_path / "errors.csv"
    with errors.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['datetime', 'clientid', 'eventdata'])
        writer.writerow(['2026-09-30T00:00:00Z', 'dev:hh', json.dumps({'sessionid': 's1', 'errordescription': {'app_version': '1.2.3', 'user_agent': 'ua', 'shakaerror': {'message': 'boom'}}})])

    lookup = analyze_errorcode_correlation.load_session_lookup(str(tmp_path))
    parsed = list(analyze_errorcode_correlation.parse_error_rows(str(errors)))

    assert lookup["s1"]["householdId"] == "hh1"
    assert parsed == [("2026-09-30", "s1", "dev:hh", "1.2.3", "ua", "boom")]


def test_analyze_errorcode_correlation_skips_bad_json(tmp_path: Path) -> None:
    errors = tmp_path / "errors.csv"
    errors.write_text("datetime,clientid,eventdata\n2026-09-30T00:00:00Z,dev,{bad json}\n", encoding="utf-8")

    assert list(analyze_errorcode_correlation.parse_error_rows(str(errors))) == []


def test_analyze_outcome_report_distribution_labels_missing() -> None:
    text, counts = analyze_outcome_report.section_outcome_distribution([
        {"playback_outcome": "DESTROY"},
        {},
    ])

    assert counts["DESTROY"] == 1
    assert counts["missing"] == 1
    assert "missing (no `unified_sessions` row)" in text


def test_analyze_outcome_report_state_sequence_flags_mismatch() -> None:
    text = analyze_outcome_report.section_state_sequence([
        {"sessionId": "s1", "playback_outcome": "INCOMPLETE_NO_DESTROY", "state_sequence": "CREATE->DESTROY", "OS Family": "Android", "Browser Name": "Chrome", "error_codes": "1003", "startup_time_ms": "12"},
    ])

    assert "HAS DESTROY (1 sessions)" in text
    assert "s1" in text


def test_analyze_session_guard_net_latency_load_rows_computes_net(tmp_path: Path) -> None:
    source = tmp_path / "latency.csv"
    source.write_text(
        "http.route,http.status_code,http.request_time,http.upstream_response_time,FCID\n"
        "/foo,200,0.25,0.10,fcid-1\n",
        encoding="utf-8",
    )

    rows = analyze_session_guard_net_latency.load_rows(str(source))

    assert rows[0]["_request_ms"] == 250.0
    assert rows[0]["_upstream_ms"] == 100.0
    assert rows[0]["_net_ms"] == 150.0


def test_analyze_session_guard_net_latency_percentile_handles_empty() -> None:
    assert analyze_session_guard_net_latency.percentile([], 95) is None


def test_analyze_webview_devices_builds_device_rollup() -> None:
    rows = [
        {"sessionId": "s1", "deviceId": "dev1", "Platform": "Android 15; Pixel Build/ABC; wv", "playback_outcome": "DESTROY", "content": "foo"},
        {"sessionId": "s2", "deviceId": "dev1", "Platform": "Android 15; Pixel Build/ABC; wv", "playback_outcome": "PLAYER_ERROR", "content": "foo"},
        {"sessionId": "s3", "deviceId": "dev1", "Platform": "Android 15; Pixel Build/ABC", "playback_outcome": "DESTROY", "content": "foo"},
    ]

    report = analyze_webview_devices.build_report_rows(rows)

    assert len(report) == 2
    assert report[0]["device_has_mixed_results"] is True
    assert report[0]["device_non_wv_success_count"] == 1


def test_analyze_webview_devices_rejects_backwards_date_range() -> None:
    with pytest.raises(ValueError, match="before --start-date"):
        list(analyze_webview_devices._daterange_ddmmyyyy("2026-10-02", "2026-10-01"))


def test_analyze_wv_device_cross_date_success_finds_source_devices(tmp_path: Path) -> None:
    source = tmp_path / "2026-09-30_setupsession_with_outcome.csv"
    source.write_text(
        "sessionId,deviceId,Platform,raw_user_agent,playback_outcome\n"
        "s1,dev1,Android 15; Pixel Build/ABC; wv,ua1,DESTROY\n"
        "s2,dev2,Android 15; Pixel Build/ABC,ua2,DESTROY\n",
        encoding="utf-8",
    )

    found = analyze_wv_device_cross_date_success.find_source_wv_devices("30092026", str(tmp_path))

    assert found == {"dev1": "ua1"}


def test_analyze_wv_device_cross_date_success_raises_on_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        analyze_wv_device_cross_date_success.find_source_wv_devices("30092026", str(tmp_path))


def test_analyze_wv_failure_then_success_devices_requires_different_success_date() -> None:
    by_device = {
        "dev1": [
            ("2026-09-30", {"Platform": "Android 15; Pixel Build/ABC; wv", "playback_outcome": "PLAYER_ERROR", "raw_user_agent": "ua", "sessionId": "s1"}),
            ("2026-10-01", {"Platform": "Android 15; Pixel Build/ABC", "playback_outcome": "DESTROY", "raw_user_agent": "ua2", "sessionId": "s2"}),
        ],
        "dev2": [
            ("2026-09-30", {"Platform": "Android 15; Pixel Build/ABC; wv", "playback_outcome": "PLAYER_ERROR", "raw_user_agent": "ua", "sessionId": "s3"}),
            ("2026-09-30", {"Platform": "Android 15; Pixel Build/ABC", "playback_outcome": "DESTROY", "raw_user_agent": "ua2", "sessionId": "s4"}),
        ],
    }

    report_rows, evidence_rows = analyze_wv_failure_then_success_devices.find_failure_then_success_devices(by_device)

    assert [row["deviceId"] for row in report_rows] == ["dev1"]
    assert {row["sessionId"] for row in evidence_rows} == {"s1", "s2"}


def test_parse_debug_user_agents_handles_android_webview_and_dedupes_rows(tmp_path: Path) -> None:
    parsed = parse_debug_user_agents.parse_user_agent(
        "Mozilla/5.0 (Linux; Android 14; SM-A047F Build/UP1A.231005.007; wv) AppleWebKit/537.36 Chrome/148.0.7778.217 Mobile Safari/537.36"
    )
    source = tmp_path / "debug.csv"
    source.write_text(
        "session_id,user_agent,hhid,shaka_message,player_phase\n"
        "s1,Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36,hh1,msg,phase\n"
        "s1,Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36,hh1,msg,phase\n",
        encoding="utf-8",
    )

    rows, total_rows = parse_debug_user_agents.load_deduped_rows(str(source))

    assert parsed["os_name"] == "Android"
    assert parsed["is_webview"] is True
    assert total_rows == 2
    assert len(rows) == 1
    assert rows[0]["device_model"] == "K (device masked - UA reduction)"
