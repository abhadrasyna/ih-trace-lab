from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from .conftest import load_script

from lib import csv_io_compat

correlate_cdn_ips = load_script("correlate_cdn_ips.py")
flatten_debug_events = load_script("flatten_debug_events.py")
lightstep_ctap_smvod_join = load_script("lightstep_ctap_smvod_join.py")
merge_ctap_smvod_csv = load_script("merge_ctap_smvod_csv.py")
process_traces = load_script("process_traces.py")


def test_flatten_debug_events_builds_superset_fieldnames() -> None:
    assert "session_id" in flatten_debug_events.ALL_FIELDNAMES
    assert "errorcode" in flatten_debug_events.ALL_FIELDNAMES
    assert len(flatten_debug_events.ALL_FIELDNAMES) == len(set(flatten_debug_events.ALL_FIELDNAMES))


def test_csv_io_compat_rejects_rows_wider_than_header() -> None:
    with pytest.raises(ValueError, match="more columns than the header defines"):
        csv_io_compat.DictReader._strip_bom_keys({"col": "value", None: ["extra"]})


def test_flatten_debug_events_main_flattens_and_warns_on_unknown_eventid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "debug.csv"
    out = tmp_path / "flat.csv"
    with source.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['datetime', 'clientid', 'eventclass', 'eventid', 'eventdata'])
        writer.writerow(['2026-09-30T00:00:00Z', 'dev:hh', 'PLAYER', 'PLAYER_ERROR', json.dumps({'sessionid': 's1', 'errorcode': '1003', 'errordescription': 'boom'})])
        writer.writerow(['2026-09-30T00:01:00Z', 'dev:hh', 'PLAYER', 'UNKNOWN', json.dumps({'sessionid': 's2'})])
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        ["flatten_debug_events.py", "--input", str(source), "--out", str(out)],
    )

    flatten_debug_events.main()

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    err = capsys.readouterr().err
    assert rows[0]["errorcode"] == "1003"
    assert rows[1]["eventid"] == "UNKNOWN"
    assert "no dedicated extractor" in err


def test_process_traces_extract_row_returns_joined_fields() -> None:
    trace = {
        "data": [
            {
                "attributes": {
                    "spans": [
                        {"tags": {"http.route": process_traces.CTAP_ROUTE, "http.user_agent": "axios/1.2.0"}},
                        {"tags": {"api": "SetupSession", "householdId": "hh1", "deviceId": "d1", "session.clientIp": "1.1.1.1", "sessionId": "s1", "contentId": "c1", "externalPackageId": "p1", "deviceType": "mobile"}},
                    ]
                }
            }
        ]
    }

    row = process_traces.extract_row(trace, source_file="trace.json")

    assert row is not None
    assert row["householdId"] == "hh1"
    assert row["Browser Name"] == "axios"


def test_process_traces_extract_row_skips_unexpected_shape(capsys: pytest.CaptureFixture[str]) -> None:
    assert process_traces.extract_row({}, source_file="trace.json") is None
    assert "unexpected trace JSON shape" in capsys.readouterr().err


def test_lightstep_join_user_agent_and_window_helpers() -> None:
    parsed = lightstep_ctap_smvod_join.parse_user_agent("Mozilla/5.0 (Mac OS X 10_15_7) AppleWebKit/537.36 Version/17.0 Safari/605.1.15")
    oldest, youngest = lightstep_ctap_smvod_join.ddmmyyyy_to_window("30092026")

    assert parsed["OS Family"] == "macOS"
    assert parsed["Browser Name"] == "Safari"
    assert oldest == "2026-09-30T00:00:00Z"
    assert youngest == "2026-10-01T00:00:00Z"
    assert lightstep_ctap_smvod_join.dec_to_hex("255") == "ff"


def test_lightstep_join_extract_row_returns_none_without_setupsession() -> None:
    trace = {"data": [{"attributes": {"spans": [{"tags": {"http.route": lightstep_ctap_smvod_join.CTAP_ROUTE, "http.user_agent": "ua"}}]}}]}

    assert lightstep_ctap_smvod_join.extract_row(trace) is None


def test_merge_ctap_smvod_csv_extracts_content_uuid_and_handles_missing_optional_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert merge_ctap_smvod_csv.extract_content_uuid("https://cdn/vode/123e4567-e89b-12d3-a456-426614174000/master.mpd") == "123e4567-e89b-12d3-a456-426614174000"

    files = merge_ctap_smvod_csv.find_input_file(str(tmp_path), "smvod-ts", "30092026", required=False)

    assert files == []
    assert "timestamps will be blank" in capsys.readouterr().err


def test_merge_ctap_smvod_csv_micros_to_iso_rejects_bad_input() -> None:
    assert merge_ctap_smvod_csv.micros_to_iso("bad") == ""


def test_correlate_cdn_ips_isolates_multi_stream_rows_by_manifest_anchor() -> None:
    rows = [
        ["2026-09-30 10:00:00.000", "", "100", "200", "", "", "TCP_HIT", "10", "https://cdn/vode/123e4567-e89b-12d3-a456-426614174000/second_screen.mpd"],
        ["2026-09-30 10:00:01.000", "", "100", "200", "", "", "TCP_HIT", "10", "https://cdn/vode/123e4567-e89b-12d3-a456-426614174000/seg1.ts"],
        ["2026-09-30 10:00:05.000", "", "100", "200", "", "", "TCP_HIT", "10", "https://cdn/vode/123e4567-e89b-12d3-a456-426614174001/second_screen.mpd"],
        ["2026-09-30 10:00:06.000", "", "100", "200", "", "", "TCP_HIT", "10", "https://cdn/vode/123e4567-e89b-12d3-a456-426614174001/seg1.ts"],
    ]

    isolated, uuid, method = correlate_cdn_ips.isolate_session_rows(rows, correlate_cdn_ips.parse_row_ts("2026-09-30 10:00:00.100"))

    assert method == "manifest_anchor_matched"
    assert uuid == "123e4567-e89b-12d3-a456-426614174000"
    assert len(isolated) == 2


def test_correlate_cdn_ips_root_cause_hint_flags_manifest_only_edge() -> None:
    hint = correlate_cdn_ips.root_cause_hint(1, 0, 0, 0, 0, manifest_only=True)

    assert hint == "manifest_only_no_segment_requests (client never requested media after manifest)"
