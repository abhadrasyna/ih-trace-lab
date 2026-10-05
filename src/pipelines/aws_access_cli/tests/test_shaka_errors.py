"""Business-logic tests for Shaka error report assembly."""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from src.pipelines.aws_access_cli import shaka_errors
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


class FakeCatalog:
    def render(self, key: str, params: dict[str, str]) -> str:
        return key


class FakeAthena:
    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses

    def start_query(self, sql: str, _params: dict[str, str]) -> str:
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=self.responses[execution_id])


def test_shaka_error_happy_path() -> None:
    athena = FakeAthena({"aws-access-cli_shaka_error_counts": [{"errorcode": "1003", "metric_value": "4"}]})

    rows = shaka_errors.build_shaka_error_report(
        athena,
        FakeCatalog(),
        DEFAULT_TENANT,
        date_value="2026-10-03",
        by="hhid",
    )

    assert rows == [
        {
            "session_date": "2026-10-03",
            "errorcode": "1003",
            "metric_value": "4",
            "report_name": "shaka_error_hhid",
        }
    ]


def test_shaka_error_rejects_reversed_range_edge_case() -> None:
    with pytest.raises(ValueError, match="end_date"):
        shaka_errors.build_shaka_error_report(
            FakeAthena({"aws-access-cli_shaka_error_counts": []}),
            FakeCatalog(),
            DEFAULT_TENANT,
            start_date="2026-10-05",
            end_date="2026-10-03",
            period="week",
        )


def test_shaka_error_logs_run_start_and_row_count(caplog: pytest.LogCaptureFixture) -> None:
    athena = FakeAthena({"aws-access-cli_shaka_error_counts": [{"errorcode": "1003", "metric_value": "4"}]})

    with caplog.at_level(logging.INFO, logger="src.pipelines.aws_access_cli.shaka_errors"):
        shaka_errors.build_shaka_error_report(
            athena,
            FakeCatalog(),
            DEFAULT_TENANT,
            start_date="2026-10-03",
            end_date="2026-10-03",
            period="day",
            by="hhid",
        )

    start_record = next(record for record in caplog.records if record.getMessage() == "Processing Shaka error report")
    end_record = next(record for record in caplog.records if record.getMessage() == "Produced Shaka error report rows")
    assert start_record.tenant == DEFAULT_TENANT.code  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.
    assert start_record.report == "shaka_error_hhid"  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.
    assert end_record.row_count == 1  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.


# Ports of `aws-access-cli`'s pre-migration `tests/shaka_errors/test_shaka_error_column_merge.py`
# cases -- same fixed-order/zero-fill/new-column semantics, just against the pure
# `pivot_error_counts` function instead of the old stateful `_MonthlyReport` object.
_KNOWN_CODES = ("1001", "1002", "6001")


def test_pivot_fills_zero_for_known_codes_absent_that_day() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "1001", "metric_value": "5"}], "2026-08-01", known_error_codes=_KNOWN_CODES
    )

    assert row == {"session_date": "2026-08-01", "1001": "5", "1002": "0", "6001": "0"}


def test_pivot_appends_new_unseen_code_at_the_end() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "1001", "metric_value": "5"}, {"errorcode": "E31012", "metric_value": "2"}],
        "2026-08-01",
        known_error_codes=_KNOWN_CODES,
    )

    assert list(row.keys()) == ["session_date", "1001", "1002", "6001", "E31012"]
    assert row["E31012"] == "2"


def test_pivot_preserves_previously_discovered_column_and_zero_fills_it_later() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "1001", "metric_value": "1"}],
        "2026-08-02",
        known_error_codes=_KNOWN_CODES,
        existing_columns=["1001", "1002", "6001", "E31012"],
    )

    assert list(row.keys()) == ["session_date", "1001", "1002", "6001", "E31012"]
    assert row["E31012"] == "0"


def test_pivot_appends_multiple_new_codes_in_sorted_order() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "9999", "metric_value": "1"}, {"errorcode": "3016", "metric_value": "2"}],
        "2026-08-01",
        known_error_codes=_KNOWN_CODES,
    )

    assert list(row.keys()) == ["session_date", "1001", "1002", "6001", "3016", "9999"]


def test_pivot_drops_rows_with_missing_errorcode() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "", "metric_value": "9"}, {"errorcode": "1001", "metric_value": "5"}],
        "2026-08-01",
        known_error_codes=_KNOWN_CODES,
    )

    assert row == {"session_date": "2026-08-01", "1001": "5", "1002": "0", "6001": "0"}


def test_pivot_sums_duplicate_errorcode_rows_instead_of_overwriting() -> None:
    row = shaka_errors.pivot_error_counts(
        [{"errorcode": "1001", "metric_value": "5"}, {"errorcode": "1001", "metric_value": "3"}],
        "2026-08-01",
        known_error_codes=_KNOWN_CODES,
    )

    assert row["1001"] == "8"
