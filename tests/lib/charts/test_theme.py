from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import pytest

from src.lib.charts import theme
from src.lib.charts.theme import DARK, FALLBACK_FONT_FAMILY, ChartTheme, chart_font_family, dim, resolve_colour


def test_dark_tokens_match_guide() -> None:
    assert ChartTheme(
        bg="#0e1117",
        ink="#e5e7eb",
        muted="#8b93a3",
        faint="#222937",
        green="#5ec8b4",
        red="#f0877f",
        amber="#e9b872",
        fill_alpha_green=0.22,
        fill_alpha_red=0.14,
        series=("#7fa8f5", "#a99bf0", "#e79bc2", "#8e9ab0", "#d9b88f"),
    ) == DARK


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


def test_amber_token_not_in_series() -> None:
    assert DARK.amber not in DARK.series


def test_dim_blends_towards_background() -> None:
    dimmed = dim(DARK.red, DARK)
    assert dimmed != DARK.red and dimmed.startswith("#") and len(dimmed) == 7
    assert dim(DARK.bg, DARK) == DARK.bg


def test_resolve_colour_names_and_dim_prefix() -> None:
    assert resolve_colour("green", DARK) == DARK.green
    assert resolve_colour("blue", DARK) == DARK.series[0]
    assert resolve_colour("dim_red", DARK) == dim(DARK.red, DARK)
    with pytest.raises(ValueError):
        resolve_colour("teal", DARK)


def test_series_has_no_status_colour() -> None:
    assert not {DARK.green, DARK.red, DARK.amber} & set(DARK.series)
    assert len(DARK.series) == 5
