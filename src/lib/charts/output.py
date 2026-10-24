"""Where chart PNGs are saved: ``<output_dir>/<tenant>/charts/``, kept apart from the CSV/XLSX reports."""

from __future__ import annotations

from pathlib import Path

CHARTS_SUBDIR = "charts"


def chart_path(output_dir: Path, tenant: str, filename: str) -> Path:
    """Returns ``<output_dir>/<tenant>/charts/<filename>`` without touching the filesystem."""
    return output_dir / tenant / CHARTS_SUBDIR / filename


def write_chart_png(png: bytes, output_dir: Path, tenant: str, filename: str) -> Path:
    """Writes ``png`` under the tenant's charts folder, creating it on first use, and returns the path."""
    path = chart_path(output_dir, tenant, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path
