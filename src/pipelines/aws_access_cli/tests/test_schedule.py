"""Tests for aws_access_cli scheduling and entry-point logging."""
from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from src.lib.logging.bootstrap import init_logging
from src.lib.logging.context import FcidLogFilter, _fcid_var
from src.pipelines.aws_access_cli import schedule
from src.pipelines.aws_access_cli.scripts import common, run_daily_reports
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    token = _fcid_var.set(None)
    for handler in original_handlers:
        root.removeHandler(handler)
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)
    _fcid_var.reset(token)


def test_run_daily_reports_calls_init_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def fake_init_logging(slug: str) -> str:
        events.append(f"init:{slug}")
        return "fcid"

    def fake_run_for_all_tenants(*_args, **_kwargs) -> int:
        events.append("run")
        return 0

    monkeypatch.setattr(run_daily_reports, "init_logging", fake_init_logging)
    monkeypatch.setattr(schedule, "run_for_all_tenants", fake_run_for_all_tenants)

    result = run_daily_reports.main(["--date", "2026-10-03"])

    assert result == 0
    assert events == ["init:aws-access-cli-daily-reports"] + ["run"] * 8


def test_catch_up_days_covers_gap_oldest_first() -> None:
    days = schedule.catch_up_days("2026-10-07", 7)
    assert days[0] == "2026-09-30"
    assert days[-1] == "2026-10-07"
    assert "2026-10-03" in days and len(days) == 8


def test_catch_up_zero_lookback_is_single_period() -> None:
    assert schedule.catch_up_days("2026-10-07", 0) == ["2026-10-07"]
    assert schedule.catch_up_weeks("2026-10-05", 0) == ["2026-10-05"]
    assert schedule.catch_up_months("2026-10", 0) == ["2026-10"]


def test_catch_up_weeks_and_months_cross_year() -> None:
    assert schedule.catch_up_weeks("2026-01-05", 2) == ["2025-12-22", "2025-12-29", "2026-01-05"]
    assert schedule.catch_up_months("2026-01", 2) == ["2025-11", "2025-12", "2026-01"]


def test_run_daily_reports_no_catch_up_runs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(run_daily_reports, "init_logging", lambda _slug: "fcid")
    monkeypatch.setattr(schedule, "run_for_all_tenants", lambda *_a, **_k: calls.append(1) or 0)

    assert run_daily_reports.main(["--date", "2026-10-07", "--no-catch-up"]) == 0
    assert len(calls) == 1


def test_run_daily_reports_force_only_on_target_date(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake(build_argv, *_a, **_k) -> int:
        seen.append(build_argv(DEFAULT_TENANT))
        return 0

    monkeypatch.setattr(run_daily_reports, "init_logging", lambda _slug: "fcid")
    monkeypatch.setattr(schedule, "run_for_all_tenants", fake)

    run_daily_reports.main(["--date", "2026-10-07", "--force"])
    assert ["--force" in argv for argv in seen] == [False] * 7 + [True]


def test_run_adoption_cli_preview_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    prints: list[tuple[object, ...]] = []
    rows = [{"session_date": "2026-10-03", "Home": "7"}]

    class FakeWriter:
        def write_rows(self, *_args, **_kwargs) -> None:
            return None

    class FakeReader:
        def read_rows(self, *_args, **_kwargs):
            return iter(())

    class FakeResolver:
        def format_snapshot_filename(self, *_args, **_kwargs) -> str:
            return "2026-10-03_adoption-report.csv"

        def format_range_filename(self, *_args, **_kwargs) -> str:
            return "2026-10-03_2026-10-03_adoption-report.csv"

        def format_month_filename(self, *_args, **_kwargs) -> str:
            return "2026-10_adoption-report.csv"

    monkeypatch.setattr(common, "make_auth", lambda: type("Auth", (), {"ensure_session": staticmethod(lambda _profile: None)})())
    monkeypatch.setattr(common, "make_athena_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)
    monkeypatch.setattr(common, "make_path_resolver", lambda: FakeResolver())
    monkeypatch.setattr(common, "make_csv_writer", lambda: FakeWriter())
    monkeypatch.setattr(common, "make_csv_reader", lambda: FakeReader())
    monkeypatch.setattr(common, "render_summary", lambda _rows: "summary")
    monkeypatch.setattr("builtins.print", lambda *args, **_kwargs: prints.append(args))

    assert common.run_adoption_cli(["--date", "2026-10-03", "--tenant", "ZA"], artifact="adoption-report", metrics=()) == 0
    assert prints == []

    assert (
        common.run_adoption_cli(
            ["--date", "2026-10-03", "--tenant", "ZA", "--preview"],
            artifact="adoption-report",
            metrics=(),
        )
        == 0
    )
    assert prints == [("summary",)]


def test_schedule_failure_logs_once_with_fcid(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schedule, "all_tenants", lambda: [DEFAULT_TENANT])
    report = schedule.SubReport("boom", lambda _argv: (_ for _ in ()).throw(RuntimeError("boom")))
    fcid = init_logging("aws-access-cli-schedule-test", to_file=False)
    original_propagate = schedule.LOGGER.propagate
    schedule.LOGGER.propagate = False
    caplog.handler.addFilter(FcidLogFilter())
    try:
        schedule.LOGGER.addHandler(caplog.handler)
        with caplog.at_level(logging.ERROR, logger="src.pipelines.aws_access_cli.schedule"):
            result = schedule.run_for_all_tenants(lambda _tenant: ["--tenant", "ZA"], [report])
    finally:
        schedule.LOGGER.removeHandler(caplog.handler)
        schedule.LOGGER.propagate = original_propagate

    assert result == 1
    error_records = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert error_records[0].getMessage() == "Scheduled sub-report failed"
    assert error_records[0].fcid == fcid  # type: ignore[attr-defined]  # LogRecord extra attrs are set dynamically at runtime.


def test_run_daily_reports_force_survives_unpadded_date(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(run_daily_reports, "init_logging", lambda _slug: "fcid")
    monkeypatch.setattr(schedule, "run_for_all_tenants", lambda build, *_a, **_k: seen.append(build(DEFAULT_TENANT)) or 0)

    run_daily_reports.main(["--date", "2026-10-7", "--force", "--lookback-days", "1"])
    assert ["--force" in argv for argv in seen] == [False, True]
