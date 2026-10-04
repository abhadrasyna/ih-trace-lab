"""Business-logic tests for the Shaka 1xxx position report."""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from src.pipelines.aws_access_cli import position_report
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


class FakeCatalog:
    def render(self, key: str, params: dict[str, str]) -> str:
        if key == "aws-access-cli_playback_outcome":
            return f"{key}:{params['session_filter']}"
        if key == "aws-access-cli_session_debug_events":
            return f"{key}:{params['id_list']}"
        return key


class FakeAthena:
    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses

    def start_query(self, sql: str, _params: dict[str, str]) -> str:
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=self.responses[execution_id])


def test_position_report_happy_path() -> None:
    athena = FakeAthena(
        {
            "aws-access-cli_error_1xxx_session_ids": [{"session_id": "s-1"}],
            "aws-access-cli_playback_outcome:AND parent_session_id IN ('s-1')": [
                {"sessionId": "s-1", "householdId": "hh-1", "deviceId": "dev-1", "event_start": "2026-10-03T10:00:00Z"}
            ],
            "aws-access-cli_session_debug_events:'s-1'": [
                {
                    "datetime": "2026-10-03T10:00:01.000Z",
                    "eventid": "STATE",
                    "session_id": "s-1",
                    "eventdata": '{"eventtype":"PLAYING","position":"1.0"}',
                },
                {
                    "datetime": "2026-10-03T10:00:02.000Z",
                    "eventid": "STATE",
                    "session_id": "s-1",
                    "eventdata": '{"eventtype":"BUFFERING","position":"2.0","errorcode":"1003","errordescription":"fail"}',
                },
            ],
        }
    )

    rows = position_report.run_position_report(athena, FakeCatalog(), DEFAULT_TENANT, "2026-10-03")

    assert rows == [
        {
            "householdId": "hh-1",
            "deviceId": "dev-1",
            "sessionId": "s-1",
            "start_time": "2026-10-03T10:00:00Z",
            "error_codes": "1003",
            "error_descriptions": "fail",
            "state_sequence": "PLAYING->ERROR(1003)",
            "min_position": "1.0",
            "max_position": "2.0",
            "position_not_moved": "False",
        }
    ]


def test_position_report_missing_sessions_edge_case() -> None:
    athena = FakeAthena({"aws-access-cli_error_1xxx_session_ids": []})

    rows = position_report.run_position_report(athena, FakeCatalog(), DEFAULT_TENANT, "2026-10-03")

    assert rows == []


def test_position_report_logs_run_start_and_row_count(caplog: pytest.LogCaptureFixture) -> None:
    athena = FakeAthena(
        {
            "aws-access-cli_error_1xxx_session_ids": [{"session_id": "s-1"}],
            "aws-access-cli_playback_outcome:AND parent_session_id IN ('s-1')": [
                {"sessionId": "s-1", "householdId": "hh-1", "deviceId": "dev-1", "event_start": "2026-10-03T10:00:00Z"}
            ],
            "aws-access-cli_session_debug_events:'s-1'": [
                {"datetime": "2026-10-03T10:00:01.000Z", "eventid": "STATE", "session_id": "s-1", "eventdata": '{"eventtype":"PLAYING","position":"1.0"}'}
            ],
        }
    )

    with caplog.at_level(logging.INFO, logger="src.pipelines.aws_access_cli.position_report"):
        position_report.run_position_report(athena, FakeCatalog(), DEFAULT_TENANT, "2026-10-03")

    start_record = next(record for record in caplog.records if record.getMessage() == "Processing position report")
    end_record = next(record for record in caplog.records if record.getMessage() == "Produced position report rows")
    assert start_record.tenant == DEFAULT_TENANT.code  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.
    assert start_record.report == "position_report"  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.
    assert end_record.row_count == 1  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.
