"""Tests for ``src.lib.logging.bootstrap``."""

from __future__ import annotations

import contextvars
import logging
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.lib.logging import setup as _logging_setup_mod
from src.lib.logging.context import FcidLogFilter, _fcid_var, current_fcid
from src.lib.logging.bootstrap import init_logging


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    fcid_token = _fcid_var.set(None)
    for handler in original_handlers:
        root.removeHandler(handler)
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)
    _fcid_var.reset(fcid_token)


def test_init_logging_binds_fcid_and_makes_it_visible_in_log_records() -> None:
    records: list[logging.LogRecord] = []
    root = logging.getLogger()

    class CapturingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    fcid = init_logging("aws-access-cli-daily-reports", to_file=False)
    handler = CapturingHandler()
    handler.addFilter(FcidLogFilter())
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    try:
        logging.getLogger("tests.bootstrap").info("hello")
    finally:
        root.removeHandler(handler)

    assert re.fullmatch(r"aws-access-cli-daily-reports-\d{8}T\d{6}-[0-9a-f]{8}", fcid)
    assert current_fcid() == fcid
    assert any(getattr(record, "fcid", None) == fcid for record in records)


def test_init_logging_twice_replaces_handlers_instead_of_duplicating_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "data_paths.yaml").write_text("logs_root: custom_logs\n", encoding="utf-8")

    contextvars.copy_context().run(init_logging, "first-run")
    first_handlers = list(logging.getLogger().handlers)
    contextvars.copy_context().run(init_logging, "second-run")
    second_handlers = list(logging.getLogger().handlers)

    assert len(first_handlers) == len(second_handlers) == 2
    assert len({id(handler) for handler in second_handlers}) == 2
    assert all(first is not second for first, second in zip(first_handlers, second_handlers, strict=True))
