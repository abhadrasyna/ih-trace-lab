"""Per-date log file naming and pruning, opt-in through ``init_logging``."""

from __future__ import annotations

import logging
import re
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def dated_log_path(log_dir: Path, file_prefix: str, day: Date) -> Path:
    return log_dir / f"{file_prefix}_{day.isoformat()}.log"


def prune_dated_logs(log_dir: Path, file_prefix: str, *, keep_days: int, today: Date, current: Path) -> list[Path]:
    """Deletes ``<file_prefix>_YYYY-MM-DD.log`` files dated more than ``keep_days`` before ``today``.

    Only files matching that exact name pattern are touched; ``current`` is never deleted.
    """
    pattern = re.compile(rf"{re.escape(file_prefix)}_(\d{{4}}-\d{{2}}-\d{{2}})\.log")
    cutoff = today - timedelta(days=keep_days)
    removed: list[Path] = []
    for path in sorted(log_dir.glob(f"{file_prefix}_*.log")):
        match = pattern.fullmatch(path.name)
        if not match or path == current:
            continue
        try:
            file_day = Date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if file_day < cutoff:
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed
