"""Where the DRM analysis scripts write: ``<base>/<OPCO>/drm-analysis/`` with ``csv/`` and ``charts/`` inside."""
from __future__ import annotations

from pathlib import Path

DRM_ANALYSIS_DIR = "drm-analysis"
CSV_SUBDIR = "csv"


def drm_analysis_dir(base: Path, opco: str) -> Path:
    """``<base>/<opco>/drm-analysis``, holding the markdown reports; no filesystem access."""
    return base / opco / DRM_ANALYSIS_DIR


def drm_csv_dir(analysis_dir: Path) -> Path:
    """The ``csv/`` folder inside a DRM analysis folder."""
    return analysis_dir / CSV_SUBDIR
