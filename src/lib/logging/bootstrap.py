"""Single-call logging bootstrap for entry points."""

from __future__ import annotations

import logging
from datetime import date as Date
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.lib.logging.context import bind_fcid
from src.lib.logging.dated_logs import dated_log_path, prune_dated_logs
from src.lib.logging.setup import setup_logging

LOGGER = logging.getLogger(__name__)


def init_logging(
    entry_point_slug: str,
    *,
    level: str = "INFO",
    to_file: bool = True,
    log_dir: Path | None = None,
    file_prefix: str | None = None,
    date: Date | None = None,
    keep_days: int | None = None,
) -> str:
    """Configure logging once and bind this run's FCID.

    Passing ``log_dir``, ``file_prefix`` and ``date`` writes ``<log_dir>/<file_prefix>_<date>.log`` (appending)
    instead of the shared ``app.log``; ``keep_days`` then prunes this prefix's files older than that many days.
    """
    timestamp = datetime.now(timezone.utc)
    fcid = f"{entry_point_slug}-{timestamp:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
    dated = (log_dir, file_prefix, date)
    if any(dated) and not all(dated):
        raise ValueError("log_dir, file_prefix and date must be given together")
    log_file = dated_log_path(log_dir, file_prefix, date) if log_dir and file_prefix and date else None
    setup_logging(level=level, to_file=to_file, log_file=log_file)
    bind_fcid(fcid)
    if log_file is not None and keep_days is not None:
        for path in prune_dated_logs(log_dir, file_prefix, keep_days=keep_days, today=timestamp.date(), current=log_file):
            LOGGER.info("pruned old log file %s", path)
    return fcid
