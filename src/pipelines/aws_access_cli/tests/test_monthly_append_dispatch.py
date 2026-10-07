"""Dispatch tests: which artifacts append into a month file vs. get a per-day snapshot."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.pipelines.aws_access_cli import adoption
from src.pipelines.aws_access_cli.scripts import common
from src.pipelines.aws_access_cli.tenants import DEFAULT_TENANT


class FakeAthena:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def start_query(self, sql: str, _params: dict[str, str]) -> str:
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=self._rows)


class FakeCatalog:
    def render(self, key: str, _params: dict[str, str]) -> str:
        return key


def _patch_common_collaborators(monkeypatch: pytest.MonkeyPatch, *, rows: list[dict[str, str]]) -> None:
    monkeypatch.setattr(common, "make_auth", lambda: SimpleNamespace(ensure_session=lambda _profile: None))
    monkeypatch.setattr(common, "make_athena_client", lambda *_args, **_kwargs: FakeAthena(rows))
    monkeypatch.setattr(common, "QueryCatalog", lambda: FakeCatalog())
    monkeypatch.setattr(common, "get_tenant", lambda _code: DEFAULT_TENANT)


def test_adoption_report_day_run_appends_into_month_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)

    common.run_adoption_cli(
        ["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="adoption-report",
        metrics=adoption.HOUSEHOLD_METRICS,
    )

    month_file = tmp_path / "ZA" / "daily" / "2026-08_adoption-report.csv"
    daily_snapshot = tmp_path / "ZA" / "daily" / "2026-08-01_adoption-report.csv"
    assert month_file.is_file()
    assert not daily_snapshot.is_file()


def test_adoption_report_rerun_of_same_day_does_not_duplicate_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)
    argv = ["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)]

    common.run_adoption_cli(argv, artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    common.run_adoption_cli([*argv, "--force"], artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)

    month_file = tmp_path / "ZA" / "daily" / "2026-08_adoption-report.csv"
    assert month_file.read_text(encoding="utf-8").count("2026-08-01") == 1


def test_adoption_report_skips_athena_when_date_already_in_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    calls: list[int] = []
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: calls.append(1) or rows)
    argv = ["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)]

    common.run_adoption_cli(argv, artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    common.run_adoption_cli(argv, artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    assert calls == [1]

    common.run_adoption_cli([*argv, "--force"], artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    assert calls == [1, 1]


def test_adoption_report_fires_athena_for_a_new_date_in_an_existing_month_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    calls: list[int] = []
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: calls.append(1) or [{"session_date": _args[3], "Home": "7"}])
    base = ["--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)]

    common.run_adoption_cli(["--date", "2026-08-01", *base], artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    common.run_adoption_cli(["--date", "2026-08-02", *base], artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)

    assert calls == [1, 1]


def test_gap_analysis_report_still_gets_a_per_day_snapshot_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home-Screen-UnqHHID": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)

    common.run_adoption_cli(
        ["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="adoption-gap-analysis",
        metrics=adoption.GAP_HOUSEHOLD_METRICS,
    )

    assert (tmp_path / "ZA" / "daily" / "2026-08-01_adoption-gap-analysis.csv").is_file()
    assert not (tmp_path / "ZA" / "daily" / "2026-08_adoption-gap-analysis.csv").is_file()


def test_shaka_error_hhid_day_run_appends_into_month_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "errorcode": "1003", "metric_value": "4", "report_name": "shaka_error_hhid"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_shaka_error_report", lambda *_args, **_kwargs: rows)

    common.run_shaka_cli(
        ["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="shaka-error-hhid",
        by="hhid",
    )

    assert (tmp_path / "ZA" / "daily" / "2026-08_shaka-error-hhid.csv").is_file()
    assert not (tmp_path / "ZA" / "daily" / "2026-08-01_shaka-error-hhid.csv").is_file()


def test_position_report_artifact_keeps_per_day_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "errorcode": "1003", "metric_value": "4", "report_name": "shaka-1xxx-position-report"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "run_position_report", lambda *_args, **_kwargs: rows)

    common.run_position_cli(["--date", "2026-08-01", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)])

    assert (tmp_path / "ZA" / "daily" / "2026-08-01_shaka-1xxx-position-report.csv").is_file()
    assert not (tmp_path / "ZA" / "daily" / "2026-08_shaka-1xxx-position-report.csv").is_file()


def test_adoption_report_week_run_appends_into_perpetual_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-03", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)

    common.run_adoption_cli(
        ["--week", "2026-08-03", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="adoption-report",
        metrics=adoption.HOUSEHOLD_METRICS,
    )

    perpetual_file = tmp_path / "ZA" / "weekly" / "adoption-report.csv"
    range_file = tmp_path / "ZA" / "weekly" / "2026-08-03_2026-08-09_adoption-report.csv"
    assert perpetual_file.is_file()
    assert not range_file.is_file()


def test_adoption_report_month_rerun_does_not_duplicate_rows_in_perpetual_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-01", "Home": "7"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_adoption_report", lambda *_args, **_kwargs: rows)
    argv = ["--month", "2026-08", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)]

    common.run_adoption_cli(argv, artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)
    common.run_adoption_cli(argv, artifact="adoption-report", metrics=adoption.HOUSEHOLD_METRICS)

    perpetual_file = tmp_path / "ZA" / "monthly" / "adoption-report.csv"
    assert perpetual_file.read_text(encoding="utf-8").count("2026-08-01") == 1


def test_shaka_error_session_week_run_pivots_into_wide_perpetual_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"session_date": "2026-08-03", "errorcode": "1003", "metric_value": "4", "report_name": "shaka_error_session"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_shaka_error_report", lambda *_args, **_kwargs: rows)

    common.run_shaka_cli(
        ["--week", "2026-08-03", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="shaka-error-session",
        by="session",
    )

    perpetual_file = tmp_path / "ZA" / "weekly" / "shaka-error-session.csv"
    content = perpetual_file.read_text(encoding="utf-8")
    assert "errorcode" not in content  # pivoted wide, not the long raw-row shape
    assert "1001,1002,1003" in content.splitlines()[0]
    assert content.splitlines()[1].split(",")[0] == "2026-08-03"


def test_shaka_error_session_second_month_preserves_newly_discovered_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_common_collaborators(monkeypatch, rows=[])
    argv = ["--month", "2026-08", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)]

    monkeypatch.setattr(
        common,
        "build_shaka_error_report",
        lambda *_args, **_kwargs: [{"session_date": "2026-08-01", "errorcode": "9999", "metric_value": "2", "report_name": "shaka_error_session"}],
    )
    common.run_shaka_cli(argv, artifact="shaka-error-session", by="session")

    monkeypatch.setattr(
        common,
        "build_shaka_error_report",
        lambda *_args, **_kwargs: [{"session_date": "2026-09-01", "errorcode": "1001", "metric_value": "1", "report_name": "shaka_error_session"}],
    )
    common.run_shaka_cli(
        ["--month", "2026-09", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
        artifact="shaka-error-session",
        by="session",
    )

    perpetual_file = tmp_path / "ZA" / "monthly" / "shaka-error-session.csv"
    lines = perpetual_file.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    assert header.endswith("9999")
    second_row = next(line for line in lines[1:] if line.startswith("2026-09-01"))
    assert second_row.endswith(",0")  # 9999 not seen this month -> zero-filled, column still kept


def test_shaka_error_cli_refuses_to_append_onto_a_stale_long_format_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stale_file = tmp_path / "ZA" / "daily" / "2026-08_shaka-error-session.csv"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("session_date,errorcode,metric_value,report_name\n2026-08-01,1003,4,shaka_error_session\n", encoding="utf-8")
    rows = [{"session_date": "2026-08-02", "errorcode": "1003", "metric_value": "4", "report_name": "shaka_error_session"}]
    _patch_common_collaborators(monkeypatch, rows=rows)
    monkeypatch.setattr(common, "build_shaka_error_report", lambda *_args, **_kwargs: rows)

    with pytest.raises(ValueError, match="long-format"):
        common.run_shaka_cli(
            ["--date", "2026-08-02", "--tenant", "ZA", "--skip-auth-check", "--output-dir", str(tmp_path)],
            artifact="shaka-error-session",
            by="session",
        )
