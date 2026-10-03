"""Targeted regression tests for the aws_access_cli port."""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.pipelines.aws_access_cli import adoption, position_report, schedule, shaka_errors
from src.pipelines.aws_access_cli.scripts import common
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


class RecordingWriter:
    def __init__(self) -> None:
        self.path: str | None = None
        self.rows: list[dict[str, str]] | None = None
        self.fieldnames: list[str] | None = None

    def write_rows(self, path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        self.path = path
        self.rows = rows
        self.fieldnames = fieldnames


class FakeCatalog:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def render(self, key: str, params: dict[str, str]) -> str:
        self.calls.append((key, params))
        return key


class FakeAthena:
    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses
        self.started_sql: list[str] = []

    def start_query(self, sql: str, _: dict[str, str]) -> str:
        self.started_sql.append(sql)
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=self.responses[execution_id])


class FakeResolver:
    def format_snapshot_filename(self, *_args, **_kwargs) -> str:
        return "2026-10-03_adoption-report.csv"

    def format_range_filename(self, *_args, **_kwargs) -> str:
        return "2026-10-01_2026-10-03_adoption-report.csv"

    def format_rollup_filename(self, artifact: str) -> str:
        return f"{artifact}_rollup.csv"


def test_resolve_range_expands_week_and_month() -> None:
    week_args = argparse.Namespace(
        date=None,
        start_date=None,
        end_date=None,
        week="2026-09-24",
        month=None,
        period="day",
    )
    month_args = argparse.Namespace(
        date=None,
        start_date=None,
        end_date=None,
        week=None,
        month="2026-02",
        period="day",
    )

    assert common.resolve_range(week_args) == ("2026-09-24", "2026-09-30", "week")
    assert common.resolve_range(month_args) == ("2026-02-01", "2026-02-28", "month")


def test_resolve_range_rejects_reversed_explicit_range() -> None:
    args = argparse.Namespace(
        date=None,
        start_date="2026-10-05",
        end_date="2026-10-03",
        week=None,
        month=None,
        period="day",
    )

    with pytest.raises(ValueError, match="end_date"):
        common.resolve_range(args)


def test_run_adoption_cli_dry_run_skips_auth_and_queries(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("dry-run should not call runtime collaborators")

    monkeypatch.setattr(common, "make_auth", fail)
    monkeypatch.setattr(common, "make_athena_client", fail)
    monkeypatch.setattr(common, "build_adoption_report", fail)
    monkeypatch.setattr(common, "make_path_resolver", lambda: FakeResolver())

    result = common.run_adoption_cli(
        ["--date", "2026-10-03", "--tenant", "ZA", "--dry-run"],
        artifact="adoption-report",
        metrics=adoption.HOUSEHOLD_METRICS,
    )

    assert result == 0
    assert "DRY RUN adoption-report" in capsys.readouterr().out


def test_run_query_cli_dry_run_renders_resolved_date_params(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = FakeCatalog()

    def fail(*_args, **_kwargs):
        raise AssertionError("dry-run should not call runtime collaborators")

    monkeypatch.setattr(common, "QueryCatalog", lambda: catalog)
    monkeypatch.setattr(common, "make_auth", fail)
    monkeypatch.setattr(common, "make_athena_client", fail)

    result = common.run_query_cli(
        ["aws-access-cli_playback_outcome", "--date", "2026-10-03", "--tenant", "ZA", "--dry-run"],
    )

    assert result == 0
    assert catalog.calls[0][1]["date"] == "2026-10-03"
    assert catalog.calls[0][1]["end_date_exclusive"] == "2026-10-04"
    assert "aws-access-cli_playback_outcome" in capsys.readouterr().out


def test_adoption_write_report_uses_metric_columns_even_when_rows_are_sparse(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = RecordingWriter()
    path = Path("output/report.csv")
    rows = [{"session_date": "2026-10-03", "Home-Screen-UnqHHID": "7"}]
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    adoption.write_report(path, writer, rows, adoption.HOUSEHOLD_METRICS[:2])

    assert writer.fieldnames == ["session_date", "Home-Screen-UnqHHID", "attempts-unique-hhid"]


def test_build_shaka_error_report_labels_period_rows_with_requested_start_date() -> None:
    catalog = FakeCatalog()
    athena = FakeAthena({"aws-access-cli_shaka_error_counts": [{"errorcode": "1001", "metric_value": "2"}]})

    rows = shaka_errors.build_shaka_error_report(
        athena,
        catalog,
        DEFAULT_TENANT,
        start_date="2026-09-29",
        end_date="2026-10-05",
        period="week",
        by="session",
    )

    assert rows == [{"session_date": "2026-09-29", "errorcode": "1001", "metric_value": "2", "report_name": "shaka_error_session"}]


def test_parse_position_seconds_rejects_non_finite_values() -> None:
    assert position_report.parse_position_seconds("nan") is None
    assert position_report.parse_position_seconds("inf") is None


def test_derive_session_rows_requires_two_positions_for_not_moved_flag() -> None:
    rows = position_report.derive_session_rows(
        [
            {
                "session_id": "s-1",
                "eventid": "PLAYER_POSITION",
                "datetime": "2026-10-03T10:00:00.000Z",
                "eventdata": '{"position":"3.5","eventtype":"PLAYING"}',
            }
        ]
    )

    assert rows[0].position_not_moved is None


def test_run_for_all_tenants_treats_systemexit_none_as_success(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = DEFAULT_TENANT
    monkeypatch.setattr(schedule, "all_tenants", lambda: [tenant])

    report = schedule.SubReport("ok-exit", lambda _argv: (_ for _ in ()).throw(SystemExit()))
    result = schedule.run_for_all_tenants(lambda _tenant: ["--tenant", "ZA"], [report])

    assert result == 0


def test_run_for_all_tenants_marks_exceptions_as_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = DEFAULT_TENANT
    monkeypatch.setattr(schedule, "all_tenants", lambda: [tenant])

    report = schedule.SubReport("boom", lambda _argv: (_ for _ in ()).throw(RuntimeError("boom")))
    result = schedule.run_for_all_tenants(lambda _tenant: ["--tenant", "ZA"], [report])

    assert result == 1
