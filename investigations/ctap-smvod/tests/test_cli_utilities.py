from __future__ import annotations

import csv
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from conftest import load_script

analyze_debug_sample = load_script("analyze_debug_sample.py")
build_debug_completeness_query = load_script("build_debug_completeness_query.py")
build_mtn_summary = load_script("build_mtn_summary.py")
build_webview_device_summary = load_script("build_webview_device_summary.py")
extract_position_report = load_script("extract_position_report.py")
extract_session_ids = load_script("extract_session_ids.py")
extract_session_timeline = load_script("extract_session_timeline.py")
filter_error_code_report = load_script("filter_error_code_report.py")


def test_analyze_debug_sample_reports_distribution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    sample = tmp_path / "debug.csv"
    sample.write_text(
        "eventid,errorcode,errordescription,sessionId,datetime,eventdata\n"
        "PLAYER_ERROR,1003,boom,s1,2026-09-30T00:00:00Z,{\"sample\": 1}\n"
        "PLAYER_SESSION_EVENT,,,s2,2026-09-30T00:01:00Z,{\"sample\": 2}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["analyze_debug_sample.py", "--input", str(sample)])
    init_logging = Mock()
    monkeypatch.setattr(analyze_debug_sample, "init_logging", init_logging)

    analyze_debug_sample.main()

    out = capsys.readouterr().out
    init_logging.assert_called_once_with("ctap-smvod-analyze_debug_sample")
    assert "total rows: 2" in out
    assert "PLAYER_ERROR" in out
    assert "distinct sessionIds: ['s1', 's2']" in out


def test_analyze_debug_sample_handles_empty_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    sample = tmp_path / "debug.csv"
    sample.write_text("eventid,errorcode,errordescription,sessionId,datetime,eventdata\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["analyze_debug_sample.py", "--input", str(sample)])

    analyze_debug_sample.main()

    out = capsys.readouterr().out
    assert "total rows: 0" in out
    assert "distinct sessionIds: []" in out


def test_build_debug_completeness_query_writes_catalog_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "sessions.csv"
    out = tmp_path / "query.sql"
    source.write_text("parent_session_id\nsess-2\nsess-1\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_debug_completeness_query.py",
            "--input",
            str(source),
            "--start",
            "2026-09-30T00:00:00.000Z",
            "--end",
            "2026-10-01T00:00:00.000Z",
            "--out",
            str(out),
        ],
    )
    init_logging = Mock()
    monkeypatch.setattr(build_debug_completeness_query, "init_logging", init_logging)

    build_debug_completeness_query.main()

    text = out.read_text(encoding="utf-8")
    init_logging.assert_called_once_with("ctap-smvod-build_debug_completeness_query")
    assert 'FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"' in text
    assert "'sess-1'" in text
    assert "'sess-2'" in text
    assert "Wrote query for 2 session IDs" in capsys.readouterr().err


def test_build_debug_completeness_query_rejects_missing_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "sessions.csv"
    source.write_text("sessionId\nabc\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_debug_completeness_query.py",
            "--input",
            str(source),
            "--column",
            "parent_session_id",
            "--start",
            "2026-09-30T00:00:00.000Z",
            "--end",
            "2026-10-01T00:00:00.000Z",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        build_debug_completeness_query.main()

    assert exc_info.value.code == 1
    assert "column 'parent_session_id' not found" in capsys.readouterr().err


def test_build_mtn_summary_writes_rollups(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    day1 = tmp_path / "2026-09-30_mtn_escalation_ips.csv"
    day2 = tmp_path / "2026-10-01_mtn_escalation_ips.csv"
    header = "clientIp,start_time,root_cause_hint\n"
    day1.write_text(header + "1.1.1.1,2026-09-30 10:00:00.000 UTC,network_issue_before_cdn (foo)\n", encoding="utf-8")
    day2.write_text(
        header
        + "1.1.1.1,2026-10-01 10:00:00.000 UTC,client_network_disconnect_suspected (bar)\n"
        + "2.2.2.2,2026-10-01 11:00:00.000 UTC,cdn_healthy_no_red_flags\n",
        encoding="utf-8",
    )

    build_mtn_summary.build_summary(str(tmp_path))

    all_dates = (tmp_path / "mtn_escalation_all_dates_rollup.csv").read_text(encoding="utf-8")
    by_ip = (tmp_path / "mtn_escalation_by_ip_summary_rollup.csv").read_text(encoding="utf-8")
    stderr = capsys.readouterr().out
    assert "2026-09-30" in all_dates and "2026-10-01" in all_dates
    assert "repeat_offender" in by_ip
    assert "1.1.1.1" in by_ip
    assert "repeat offender" in stderr


def test_build_mtn_summary_handles_empty_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_mtn_summary.build_summary(str(tmp_path))

    assert "nothing to summarize" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())


def test_build_mtn_summary_main_calls_init_logging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["build_mtn_summary.py", "--output-dir", str(tmp_path)])
    init_logging = Mock()
    monkeypatch.setattr(build_mtn_summary, "init_logging", init_logging)

    build_mtn_summary.main()

    init_logging.assert_called_once_with("ctap-smvod-build_mtn_summary")


def test_build_webview_device_summary_deduplicates_non_wv_counts() -> None:
    rows = [
        {
            "date": "2026-09-30",
            "deviceId": "dev-1",
            "device_model": "Pixel",
            "is_success": "true",
            "device_non_wv_success_count": "2",
            "device_non_wv_failure_count": "1",
        },
        {
            "date": "2026-09-30",
            "deviceId": "dev-1",
            "device_model": "Pixel",
            "is_success": "false",
            "device_non_wv_success_count": "2",
            "device_non_wv_failure_count": "1",
        },
    ]

    summary = build_webview_device_summary.build_summary_rows(rows)

    assert summary == [
        {
            "device_model": "Pixel",
            "distinct_device_count": 1,
            "dates_seen_count": 1,
            "date_range": "2026-09-30",
            "wv_session_count": 2,
            "wv_success_count": 1,
            "wv_failure_count": 1,
            "wv_success_rate_pct": 50.0,
            "non_wv_session_count": 3,
            "non_wv_success_count": 2,
            "non_wv_failure_count": 1,
            "non_wv_success_rate_pct": 66.7,
            "non_wv_success_when_wv_failed_flag": True,
        }
    ]


def test_build_webview_device_summary_load_rows_returns_empty_when_no_reports(tmp_path: Path) -> None:
    assert build_webview_device_summary.load_rows(str(tmp_path)) == []


def test_build_webview_device_summary_main_calls_init_logging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["build_webview_device_summary.py", "--output-dir", str(tmp_path)])
    init_logging = Mock()
    monkeypatch.setattr(build_webview_device_summary, "init_logging", init_logging)

    build_webview_device_summary.main()

    init_logging.assert_called_once_with("ctap-smvod-build_webview_device_summary")


def test_extract_position_report_filters_rows_and_warns_for_optional_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "2026-09-30_setupsession_with_outcome.csv"
    out = tmp_path / "2026-09-30_position_report.csv"
    source.write_text(
        "sessionId,position_not_moved,error_codes,start_time\n"
        "s1,true,1003; 1005,2026-09-30 10:00:00.000 UTC\n"
        "s2,false,1003,2026-09-30 11:00:00.000 UTC\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_position_report.py",
            "--date",
            "30092026",
            "--input",
            str(source),
            "--out",
            str(out),
            "--error-code",
            "1003",
        ],
    )
    init_logging = Mock()
    monkeypatch.setattr(extract_position_report, "init_logging", init_logging)

    extract_position_report.main()

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    err = capsys.readouterr().err
    init_logging.assert_called_once_with("ctap-smvod-extract_position_report")
    assert rows == [{"householdId": "", "deviceId": "", "session.clientIp": "", "sessionId": "s1", "content_uuid": "", "start_time": "2026-09-30 10:00:00.000 UTC", "error_codes": "1003; 1005", "error_descriptions": "", "state_sequence": "", "min_position": "", "max_position": "", "position_not_moved": "true"}]
    assert "leaving blank in output" in err


def test_extract_position_report_requires_session_id_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "2026-09-30_setupsession_with_outcome.csv"
    source.write_text("position_not_moved,error_codes\ntrue,1003\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["extract_position_report.py", "--date", "30092026", "--input", str(source), "--columns", "sessionId,error_codes"],
    )

    with pytest.raises(SystemExit) as exc_info:
        extract_position_report.main()

    assert exc_info.value.code == 1
    assert "'sessionId' is required and missing" in capsys.readouterr().err


def test_extract_session_ids_formats_sorted_sql_clause(tmp_path: Path) -> None:
    source = tmp_path / "report.csv"
    source.write_text("sessionId\nbeta\nalpha\nbeta\n", encoding="utf-8")

    ids = extract_session_ids.extract_ids(str(source))
    clause = extract_session_ids.format_in_clause(ids)

    assert ids == ["alpha", "beta"]
    assert clause == "(\n  'alpha',\n  'beta'\n)\n"


def test_extract_session_ids_rejects_empty_clause() -> None:
    with pytest.raises(ValueError, match="empty SQL IN clause"):
        extract_session_ids.format_in_clause([])


def test_extract_session_ids_main_calls_init_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "report.csv"
    source.write_text("sessionId\nbeta\nalpha\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["extract_session_ids.py", "--input", str(source)])
    init_logging = Mock()
    monkeypatch.setattr(extract_session_ids, "init_logging", init_logging)

    extract_session_ids.main()

    init_logging.assert_called_once_with("ctap-smvod-extract_session_ids")
    assert "'alpha'" in capsys.readouterr().out


def test_extract_session_timeline_sorts_rows_by_event_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "session.csv"
    out = tmp_path / "timeline.csv"
    source.write_text(
        "event_type,event_start,event_end,content,endreason\n"
        "BUFFERING,2026-09-30T00:02:00Z,2026-09-30T00:03:00Z,foo,\n"
        "PLAY,2026-09-30T00:01:00Z,2026-09-30T00:02:00Z,foo,DESTROY\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["extract_session_timeline.py", "--input", str(source), "--out", str(out)])
    init_logging = Mock()
    monkeypatch.setattr(extract_session_timeline, "init_logging", init_logging)

    extract_session_timeline.main()

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    init_logging.assert_called_once_with("ctap-smvod-extract_session_timeline")
    assert [row["event_type"] for row in rows] == ["PLAY", "BUFFERING"]
    assert "Wrote 2 rows" in capsys.readouterr().err


def test_extract_session_timeline_errors_on_missing_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "session.csv"
    source.write_text("event_type,event_start\nPLAY,2026-09-30T00:01:00Z\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["extract_session_timeline.py", "--input", str(source), "--columns", "event_type,endreason"])

    with pytest.raises(SystemExit) as exc_info:
        extract_session_timeline.main()

    assert exc_info.value.code == 1
    assert "column(s) ['endreason'] not found" in capsys.readouterr().err


def test_filter_error_code_report_matches_multi_value_cells() -> None:
    assert filter_error_code_report._matches_error_code("1001; 1003, 1005", "1003") is True


def test_filter_error_code_report_errors_without_valid_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["filter_error_code_report.py", "--dates", "30092026", "--input-dir", str(tmp_path)],
    )
    init_logging = Mock()
    monkeypatch.setattr(filter_error_code_report, "init_logging", init_logging)

    with pytest.raises(SystemExit) as exc_info:
        filter_error_code_report.main()

    init_logging.assert_called_once_with("ctap-smvod-filter_error_code_report")
    assert exc_info.value.code == 1
    assert "no valid input files processed" in capsys.readouterr().err
