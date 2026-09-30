"""Tests for src.lib.paths."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.lib.paths.config import PathConfig, YamlPathResolver
from src.lib.paths.protocols import PathResolver


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_resolver(root: Path) -> YamlPathResolver:
    config_path = root / "config" / "data_paths.yaml"
    _write(
        config_path,
        """data_root: data
knowledge_root: knowledge
investigations_root: investigations
tools:
  - har
  - lightstep
  - athena
templates:
  data_with_campaign: \"{data_root}/{campaign}/{case_id}/{tool}\"
  data_without_campaign: \"{data_root}/{case_id}/{tool}\"
  knowledge: \"{knowledge_root}/{tool}\"
  investigation_with_campaign: \"{investigations_root}/{campaign}\"
  investigation_without_campaign: \"{investigations_root}/{case_id}\"
  investigation_data: \"{investigations_root}/{campaign}/data/{tool}\"
  investigation_output: \"{investigations_root}/{campaign}/output\"
filename_date_format: \"%Y-%m-%d\"
""",
    )
    return YamlPathResolver(root, PathConfig.load(config_path))


class _ConformingPathResolver:
    def resolve_input_dir(self, tool: str, case_id: str, campaign: str | None = None) -> Path | None:
        return Path(tool) / case_id if campaign is None else Path(campaign) / case_id / tool

    def resolve_knowledge_dir(self, tool: str) -> Path:
        return Path("knowledge") / tool

    def resolve_investigation_dir(self, case_id: str, campaign: str | None = None) -> Path:
        return Path(case_id) if campaign is None else Path(campaign)

    def resolve_investigation_data_dir(self, slug: str, tool: str) -> Path:
        return Path(slug) / "data" / tool

    def resolve_investigation_output_dir(self, slug: str) -> Path:
        return Path(slug) / "output"

    def format_snapshot_filename(self, as_of: date, artifact: str, *, extension: str = "csv") -> str:
        return f"{as_of:%Y-%m-%d}_{artifact}.{extension}"

    def format_range_filename(
        self,
        start: date,
        end: date,
        artifact: str,
        *,
        tag: str | None = None,
        extension: str = "csv",
    ) -> str:
        suffix = f"_{tag}" if tag is not None else ""
        return f"{start:%Y-%m-%d}_{end:%Y-%m-%d}_{artifact}{suffix}.{extension}"

    def format_rollup_filename(self, artifact: str, *, extension: str = "csv") -> str:
        return f"{artifact}_rollup.{extension}"


class _MissingRollupFormatter:
    def resolve_input_dir(self, tool: str, case_id: str, campaign: str | None = None) -> Path | None:
        return Path(tool) / case_id

    def resolve_knowledge_dir(self, tool: str) -> Path:
        return Path("knowledge") / tool

    def resolve_investigation_dir(self, case_id: str, campaign: str | None = None) -> Path:
        return Path(case_id)

    def resolve_investigation_data_dir(self, slug: str, tool: str) -> Path:
        return Path(slug) / "data" / tool

    def resolve_investigation_output_dir(self, slug: str) -> Path:
        return Path(slug) / "output"

    def format_snapshot_filename(self, as_of: date, artifact: str, *, extension: str = "csv") -> str:
        return f"{as_of:%Y-%m-%d}_{artifact}.{extension}"

    def format_range_filename(
        self,
        start: date,
        end: date,
        artifact: str,
        *,
        tag: str | None = None,
        extension: str = "csv",
    ) -> str:
        return f"{start:%Y-%m-%d}_{end:%Y-%m-%d}_{artifact}.{extension}"


def test_resolve_input_dir_with_campaign_formats_data_with_campaign_template(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)
    expected = tmp_path / "data" / "applause" / "7231547" / "athena"
    expected.mkdir(parents=True)

    assert resolver.resolve_input_dir("athena", "7231547", campaign="applause") == expected


def test_resolve_input_dir_without_campaign_formats_data_without_campaign_template(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)
    expected = tmp_path / "data" / "7231547" / "har"
    expected.mkdir(parents=True)

    assert resolver.resolve_input_dir("har", "7231547") == expected


def test_resolve_input_dir_returns_none_when_directory_absent(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.resolve_input_dir("lightstep", "7231547", campaign="applause") is None


def test_resolve_knowledge_dir_ignores_campaign_and_case_id(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.resolve_knowledge_dir("athena") == tmp_path / "knowledge" / "athena"


def test_resolve_investigation_dir_with_and_without_campaign(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.resolve_investigation_dir("7231547", campaign="applause") == tmp_path / "investigations" / "applause"
    assert resolver.resolve_investigation_dir("7231547") == tmp_path / "investigations" / "7231547"


def test_resolve_investigation_data_dir_formats_investigation_data_template(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.resolve_investigation_data_dir("ctap-smvod", "lightstep") == tmp_path / "investigations" / "ctap-smvod" / "data" / "lightstep"


def test_resolve_investigation_output_dir_formats_investigation_output_template(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.resolve_investigation_output_dir("ctap-smvod") == tmp_path / "investigations" / "ctap-smvod" / "output"


def test_format_snapshot_filename_uses_iso_prefix(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.format_snapshot_filename(date(2026, 8, 1), "position_report") == "2026-08-01_position_report.csv"


def test_format_range_filename_appends_tag_as_trailing_segment_not_infix(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.format_range_filename(date(2026, 8, 1), date(2026, 8, 7), "position_report", tag="INC-1003") == "2026-08-01_2026-08-07_position_report_INC-1003.csv"


def test_format_rollup_filename_has_no_date(tmp_path: Path) -> None:
    resolver = _build_resolver(tmp_path)

    assert resolver.format_rollup_filename("position_report") == "position_report_rollup.csv"


def test_conforming_stub_satisfies_path_resolver_protocol() -> None:
    assert isinstance(_ConformingPathResolver(), PathResolver)


def test_non_conforming_stub_does_not_satisfy_protocol() -> None:
    assert not isinstance(_MissingRollupFormatter(), PathResolver)
