"""Canonical logging entrypoint — call once, at process start, before any other logging call.

Every entrypoint script and every ``src/`` module gets its logger via ``logging.getLogger(name)``
after this has run once; never call ``logging.basicConfig`` again elsewhere. Log files land under
the ``logs_root`` directory declared in ``config/data_paths.yaml`` (``logs/`` by default), appended
to a single ``app.log`` across every run (no daily split/rotation yet — that remains future work).

Lives under ``src/lib/logging/`` (not ``logs/``) so code and its own generated runtime artifact
(``logs/app.log``) aren't colocated in the same directory.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

from src.lib.logging.context import FcidLogFilter

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATA_PATHS_CONFIG = _REPO_ROOT / "config" / "data_paths.yaml"
_DEFAULT_LOGS_ROOT = "logs"
_FCID_LOG_FILTER = FcidLogFilter()


def _logs_dir() -> Path:
    """Resolves the log directory from ``config/data_paths.yaml``'s ``logs_root`` key.

    Falls back to ``logs/`` only when the config file itself is missing (e.g. a fresh checkout
    mid-bootstrap); a *present but invalid* config (unparsable YAML, a non-mapping top level, or
    a null ``logs_root``) raises instead of silently writing logs somewhere unexpected.
    """
    try:
        raw_text = _DATA_PATHS_CONFIG.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _REPO_ROOT / _DEFAULT_LOGS_ROOT

    payload = yaml.safe_load(raw_text)
    if payload is None:
        return _REPO_ROOT / _DEFAULT_LOGS_ROOT
    if not isinstance(payload, dict):
        raise TypeError(f"{_DATA_PATHS_CONFIG} must contain a YAML mapping at its top level, got {type(payload).__name__}")

    logs_root = payload.get("logs_root", _DEFAULT_LOGS_ROOT)
    if logs_root is None:
        raise ValueError(f"{_DATA_PATHS_CONFIG}'s logs_root key is present but empty; remove the key to use the default or set it to a path")
    return _REPO_ROOT / str(logs_root)


_LEVEL_NAMES = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def setup_logging(*, level: str = "INFO", to_file: bool = True) -> None:
    """Configure the root logger with a consistent line format.

    Args:
        level: Standard library level name (``DEBUG``, ``INFO``, ``WARNING``, ...). Raises
            ``ValueError`` on an unrecognized name rather than silently falling back to ``INFO``.
        to_file: When ``True``, also write to ``<logs_root>/app.log`` alongside stdout.
    """
    level_name = level.upper()
    try:
        level_value = _LEVEL_NAMES[level_name]
    except KeyError:
        raise ValueError(f"unrecognized logging level {level!r}; expected one of {sorted(_LEVEL_NAMES)}") from None

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if to_file:
        logs_dir = _logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logs_dir / "app.log"))
    for handler in handlers:
        handler.addFilter(_FCID_LOG_FILTER)

    logging.basicConfig(
        level=level_value,
        format="%(asctime)s [%(levelname)s] [%(name)s] [fcid=%(fcid)s] %(message)s",
        handlers=handlers,
        force=True,
    )
