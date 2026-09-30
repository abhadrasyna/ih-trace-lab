"""Protocol definitions for config-driven path resolution."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PathResolver(Protocol):
    """Resolve repo paths and filenames from `config/data_paths.yaml` instead of hardcoding them."""

    def resolve_input_dir(self, tool: str, case_id: str, campaign: str | None = None) -> Path | None:
        ...

    def resolve_knowledge_dir(self, tool: str) -> Path:
        ...

    def resolve_investigation_dir(self, case_id: str, campaign: str | None = None) -> Path:
        ...

    def resolve_investigation_data_dir(self, slug: str, tool: str) -> Path:
        ...

    def resolve_investigation_output_dir(self, slug: str) -> Path:
        ...

    def format_snapshot_filename(self, as_of: date, artifact: str, *, extension: str = "csv") -> str:
        ...

    def format_range_filename(
        self,
        start: date,
        end: date,
        artifact: str,
        *,
        tag: str | None = None,
        extension: str = "csv",
    ) -> str:
        ...

    def format_rollup_filename(self, artifact: str, *, extension: str = "csv") -> str:
        ...
