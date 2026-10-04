"""Single-call logging bootstrap for entry points."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.lib.logging.context import bind_fcid
from src.lib.logging.setup import setup_logging


def init_logging(entry_point_slug: str, *, level: str = "INFO", to_file: bool = True) -> str:
    """Configure logging once and bind this run's FCID."""
    timestamp = datetime.now(timezone.utc)
    fcid = f"{entry_point_slug}-{timestamp:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
    setup_logging(level=level, to_file=to_file)
    bind_fcid(fcid)
    return fcid
