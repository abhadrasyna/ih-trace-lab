"""Chart palette and font resolution — the only place colours and the font family are defined.

``theme`` imports nothing from the rest of the ``charts`` package. See ``docs/guides/chart-guidelines.md``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

FALLBACK_FONT_FAMILY = "DejaVu Sans"
BUNDLED_FONT_FAMILY = "Roboto"
FONT_FILES = ("Roboto-Regular.ttf", "Roboto-Bold.ttf")
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

_font_lock = threading.Lock()


@dataclass(frozen=True)
class ChartTheme:
    bg: str
    ink: str
    muted: str
    faint: str
    green: str
    red: str
    amber: str
    fill_alpha_green: float
    fill_alpha_red: float
    # Ordered, distinguishable on ``bg``; ``green``, ``red`` and ``amber`` stay reserved for status meaning.
    series: tuple[str, ...] = ()
    # Corner radius of bars, in inches; clamped per bar so a thin bar becomes a pill.
    corner_radius_in: float = 0.09
    # Share of ``bg`` blended into a colour by ``dim`` (the "before" / secondary look of a status colour).
    dim_amount: float = 0.38


DARK = ChartTheme(
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
)


def dim(colour: str, theme: ChartTheme) -> str:
    """Blends ``colour`` towards ``bg`` by ``theme.dim_amount``: the quieter twin used for "before" or secondary data."""
    mix = theme.dim_amount

    def channel(c: str, i: int) -> int:
        return round(int(c[i : i + 2], 16) * (1 - mix) + int(theme.bg[i : i + 2], 16) * mix)

    return "#" + "".join(f"{channel(colour, i):02x}" for i in (1, 3, 5))


STATUS_TOKENS = ("ink", "muted", "faint", "green", "red", "amber")
SERIES_NAMES = ("blue", "violet", "pink", "slate", "sand")


def resolve_colour(name: str, theme: ChartTheme) -> str:
    """Maps a semantic name to a theme colour: a status token, a series name (``blue``..``sand``) or ``dim_<either>``."""
    if name.startswith("dim_"):
        return dim(resolve_colour(name[4:], theme), theme)
    if name in STATUS_TOKENS:
        return getattr(theme, name)
    if name in SERIES_NAMES and SERIES_NAMES.index(name) < len(theme.series):
        return theme.series[SERIES_NAMES.index(name)]
    raise ValueError(f"unknown colour name {name!r}; use {STATUS_TOKENS + SERIES_NAMES} or dim_<name>")


def _register_fonts(font_dir: Path) -> str:
    """Registers the bundled Roboto files and returns the family; raises on any problem."""
    from matplotlib import font_manager

    for name in FONT_FILES:
        font_manager.fontManager.addfont(str(font_dir / name))
    return BUNDLED_FONT_FAMILY


def _resolve_family(font_dir: Path) -> str:
    with _font_lock:
        try:
            return _register_fonts(font_dir)
        except Exception as exc:  # noqa: BLE001 - contract: font loading never raises
            logger.warning("Roboto unavailable (%s); falling back to %s", exc, FALLBACK_FONT_FAMILY)
            return FALLBACK_FONT_FAMILY


@lru_cache(maxsize=1)
def chart_font_family() -> str:
    """Returns ``"Roboto"`` once registered, else ``"DejaVu Sans"``; never raises."""
    return _resolve_family(FONT_DIR)
