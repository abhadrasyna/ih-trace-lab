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
    fill_alpha_green: float
    fill_alpha_red: float


DARK = ChartTheme(
    bg="#0e1117",
    ink="#e5e7eb",
    muted="#9ca3af",
    faint="#1f2937",
    green="#26b3a0",
    red="#ef5350",
    fill_alpha_green=0.22,
    fill_alpha_red=0.14,
)


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
