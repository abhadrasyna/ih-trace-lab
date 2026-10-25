from __future__ import annotations

from pathlib import Path

from lib.drm_output import drm_analysis_dir, drm_csv_dir


def test_drm_analysis_and_csv_dirs() -> None:
    folder = drm_analysis_dir(Path("output"), "ZA")
    assert folder == Path("output/ZA/drm-analysis")
    assert drm_csv_dir(folder) == Path("output/ZA/drm-analysis/csv")


def test_dirs_are_pure_path_maths(tmp_path: Path) -> None:
    drm_analysis_dir(tmp_path, "GH")
    assert list(tmp_path.iterdir()) == []
