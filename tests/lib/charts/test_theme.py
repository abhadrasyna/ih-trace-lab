from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import pytest

from src.lib.charts import theme
from src.lib.charts.theme import DARK, FALLBACK_FONT_FAMILY, ChartTheme, chart_font_family


def test_dark_tokens_match_guide() -> None:
    assert DARK == ChartTheme(
        bg="#0e1117",
        ink="#e5e7eb",
        muted="#9ca3af",
        faint="#1f2937",
        green="#26b3a0",
        red="#ef5350",
        fill_alpha_green=0.22,
        fill_alpha_red=0.14,
    )


def test_theme_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        DARK.bg = "#000000"  # type: ignore[misc]


def test_font_family_resolves_bundled_roboto() -> None:
    chart_font_family.cache_clear()
    assert chart_font_family() == "Roboto"


def test_font_falls_back_when_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=theme.logger.name):
        family = theme._resolve_family(tmp_path / "no-such-dir")
    assert family == FALLBACK_FONT_FAMILY
    assert "falling back" in caplog.text
