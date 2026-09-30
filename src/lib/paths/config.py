"""Load and apply the project's path-layout configuration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.lib.paths.protocols import PathResolver

_TEMPLATE_NAMES = (
    "data_with_campaign",
    "data_without_campaign",
    "knowledge",
    "investigation_with_campaign",
    "investigation_without_campaign",
    "investigation_data",
    "investigation_output",
)


@dataclass(frozen=True)
class PathConfig:
    """Typed view of `config/data_paths.yaml`."""

    data_root: str
    knowledge_root: str
    investigations_root: str
    tools: tuple[str, ...]
    filename_date_format: str
    data_with_campaign: str
    data_without_campaign: str
    knowledge: str
    investigation_with_campaign: str
    investigation_without_campaign: str
    investigation_data: str
    investigation_output: str

    @classmethod
    def load(cls, path: Path) -> PathConfig:
        """Load and validate `path` as a path-layout config file."""
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        templates = payload.get("templates")
        if not isinstance(templates, dict):
            raise ValueError("config/data_paths.yaml must define a templates mapping")

        missing_root_keys = [key for key in ("data_root", "knowledge_root", "investigations_root", "tools", "filename_date_format") if key not in payload]
        if missing_root_keys:
            raise ValueError(f"config/data_paths.yaml is missing keys: {', '.join(missing_root_keys)}")

        missing_template_keys = [key for key in _TEMPLATE_NAMES if key not in templates]
        if missing_template_keys:
            raise ValueError(f"config/data_paths.yaml is missing templates: {', '.join(missing_template_keys)}")

        tools = payload["tools"]
        if not isinstance(tools, list) or any(not isinstance(tool, str) for tool in tools):
            raise ValueError("config/data_paths.yaml tools must be a list of strings")

        return cls(
            data_root=str(payload["data_root"]),
            knowledge_root=str(payload["knowledge_root"]),
            investigations_root=str(payload["investigations_root"]),
            tools=tuple(tools),
            filename_date_format=str(payload["filename_date_format"]),
            data_with_campaign=str(templates["data_with_campaign"]),
            data_without_campaign=str(templates["data_without_campaign"]),
            knowledge=str(templates["knowledge"]),
            investigation_with_campaign=str(templates["investigation_with_campaign"]),
            investigation_without_campaign=str(templates["investigation_without_campaign"]),
            investigation_data=str(templates["investigation_data"]),
            investigation_output=str(templates["investigation_output"]),
        )


class YamlPathResolver(PathResolver):
    """Resolve directories and filenames from a `PathConfig` loaded from YAML."""

    def __init__(self, repo_root: Path, config: PathConfig) -> None:
        self._repo_root = repo_root
        self._config = config

    @classmethod
    def from_file(cls, config_path: Path, repo_root: Path | None = None) -> YamlPathResolver:
        """Create a resolver from `config_path`."""
        resolved_path = config_path.resolve()
        resolved_root = repo_root.resolve() if repo_root is not None else resolved_path.parent.parent
        return cls(resolved_root, PathConfig.load(resolved_path))

    def resolve_input_dir(self, tool: str, case_id: str, campaign: str | None = None) -> Path | None:
        template = self._config.data_with_campaign if campaign is not None else self._config.data_without_campaign
        path = self._format_path(template, tool=tool, case_id=case_id, campaign=campaign)
        if not path.is_dir():
            return None
        return path

    def resolve_knowledge_dir(self, tool: str) -> Path:
        return self._format_path(self._config.knowledge, tool=tool)

    def resolve_investigation_dir(self, case_id: str, campaign: str | None = None) -> Path:
        template = self._config.investigation_with_campaign if campaign is not None else self._config.investigation_without_campaign
        return self._format_path(template, case_id=case_id, campaign=campaign)

    def resolve_investigation_data_dir(self, slug: str, tool: str) -> Path:
        return self._format_path(self._config.investigation_data, campaign=slug, tool=tool)

    def resolve_investigation_output_dir(self, slug: str) -> Path:
        return self._format_path(self._config.investigation_output, campaign=slug)

    def format_snapshot_filename(self, as_of: date, artifact: str, *, extension: str = "csv") -> str:
        return f"{self._format_date(as_of)}_{artifact}.{self._normalize_extension(extension)}"

    def format_range_filename(
        self,
        start: date,
        end: date,
        artifact: str,
        *,
        tag: str | None = None,
        extension: str = "csv",
    ) -> str:
        parts = [self._format_date(start), self._format_date(end), artifact]
        if tag is not None:
            parts.append(tag)
        return f"{'_'.join(parts)}.{self._normalize_extension(extension)}"

    def format_rollup_filename(self, artifact: str, *, extension: str = "csv") -> str:
        return f"{artifact}_rollup.{self._normalize_extension(extension)}"

    def _format_path(self, template: str, **values: Any) -> Path:
        formatted = template.format(
            data_root=self._config.data_root,
            knowledge_root=self._config.knowledge_root,
            investigations_root=self._config.investigations_root,
            **values,
        )
        return self._repo_root / formatted

    def _format_date(self, value: date) -> str:
        return value.strftime(self._config.filename_date_format)

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        return extension.lstrip(".")
