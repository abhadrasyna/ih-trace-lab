"""Protocol skeletons for shared report rendering."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReportRenderer(Protocol):
    """Strategy seam from PYTHON_DESIGN.md: render normalized rows, while csv_io owns file I/O."""

    def render(self, rows: list[dict[str, str]]) -> str:
        ...
