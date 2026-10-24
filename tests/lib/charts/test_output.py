from pathlib import Path

from src.lib.charts.output import chart_path, write_chart_png


def test_write_chart_png_creates_charts_subfolder(tmp_path: Path) -> None:
    path = write_chart_png(b"png", tmp_path, "ZA", "2026-10-14_x.png")
    assert path == tmp_path / "ZA" / "charts" / "2026-10-14_x.png"
    assert path.read_bytes() == b"png"


def test_chart_path_does_not_create_folders(tmp_path: Path) -> None:
    assert not chart_path(tmp_path, "ZA", "x.png").parent.exists()
