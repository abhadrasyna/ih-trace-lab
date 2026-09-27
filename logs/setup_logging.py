"""Canonical logging entrypoint — call once, at process start, before any other logging call.

Every entrypoint script and every ``src/`` module gets its logger via ``logging.getLogger(name)``
after this has run once; never call ``logging.basicConfig`` again elsewhere. Log files land under
this same ``logs/`` directory, one per calendar day, so cron output survives across runs.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent


def setup_logging(*, level: str = "INFO", to_file: bool = True) -> None:
    """Configure the root logger with a consistent line format.

    Args:
        level: Standard library level name (``DEBUG``, ``INFO``, ``WARNING``, ...).
        to_file: When ``True``, also write to ``logs/app.log`` alongside stdout.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if to_file:
        handlers.append(logging.FileHandler(_LOG_DIR / "app.log"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=handlers,
    )
