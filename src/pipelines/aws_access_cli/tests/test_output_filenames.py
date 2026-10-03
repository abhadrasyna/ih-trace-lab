"""Filename/path regression tests for PT-7 filename usage."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.pipelines.aws_access_cli import adoption, shaka_errors
from src.pipelines.aws_access_cli.scripts import common


class FakeResolver:
    def format_snapshot_filename(self, *_args, **_kwargs) -> str:
        return "2026-10-03_adoption-report.csv"

    def format_range_filename(self, *_args, **_kwargs) -> str:
        return "2026-10-01_2026-10-03_shaka-error-report.csv"

    def format_rollup_filename(self, artifact: str) -> str:
        return f"{artifact}_rollup.csv"


class RecordingWriter:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def write_rows(self, path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        self.paths.append(path)


class FakeAthena:
    def start_query(self, sql: str, _params: dict[str, str]) -> str:
        return sql

    def fetch_results(self, execution_id: str) -> SimpleNamespace:
        return SimpleNamespace(rows=[{"session_date": "2026-10-03", "metric_value": "1"}])


class FakeCatalog:
    def render(self, key: str, params: dict[str, str]) -> str:
        return f"{key}:{sorted(params)}"


def test_snapshot_filename_is_iso_prefixed() -> None:
    filename = adoption.resolve_filename(
        FakeResolver(),
        "adoption-report",
        start_date="2026-10-03",
        end_date="2026-10-03",
        period="day",
    )

    assert filename == "2026-10-03_adoption-report.csv"


def test_range_filename_tags_trailing() -> None:
    filename = shaka_errors.resolve_filename(
        FakeResolver(),
        "shaka-error-report",
        start_date="2026-10-01",
        end_date="2026-10-03",
        period="week",
    )

    assert filename == "2026-10-01_2026-10-03_shaka-error-report.csv"


def test_rollup_filename_has_marker(monkeypatch) -> None:
    writer = RecordingWriter()

    def record_write(path: Path, _writer, rows):
        writer.write_rows(str(path), rows, [])
        return path

    monkeypatch.setattr(common, "make_path_resolver", lambda: FakeResolver())
    monkeypatch.setattr(common, "make_auth", lambda: SimpleNamespace(ensure_session=lambda _profile: None))
    monkeypatch.setattr(common, "make_athena_client", lambda *_args, **_kwargs: FakeAthena())
    monkeypatch.setattr(common, "QueryCatalog", lambda: FakeCatalog())
    monkeypatch.setattr(common, "make_csv_writer", lambda: writer)
    monkeypatch.setattr(common, "write_shaka_report", record_write)

    result = common.run_query_cli(["aws-access-cli_playback_outcome", "--tenant", "ZA", "--skip-auth-check"])

    assert result == 0
    assert writer.paths == [str(Path(common.repo_root()) / "output" / "ZA" / "daily" / "aws-access-cli_playback_outcome_rollup.csv")]


def test_base_output_dir_defaults_to_resolved_tenant() -> None:
    args = SimpleNamespace(output_dir="output", tenant=None)

    output_dir = common._base_output_dir(args, "day")

    assert output_dir == common.repo_root() / "output" / "ZA" / "daily"
