"""Tests for `src.lib.logging.setup`'s canonical `setup_logging()` entrypoint."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from src.lib.logging import setup as _logging_setup_mod
from src.lib.logging.setup import setup_logging


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Iterator[None]:
    """Clears the root logger's handlers around each test.

    `logging.basicConfig()` is a no-op once the root logger already has a handler (e.g. pytest's
    own `caplog` handler) -- clearing before `yield` lets `setup_logging()`'s `basicConfig` call
    actually take effect for the test; restoring after `yield` prevents the test's handlers from
    leaking into later tests or pytest's own logging capture.
    """
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    for handler in original_handlers:
        root.removeHandler(handler)
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)


def test_setup_logging_writes_to_configured_logs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file handler is created under the `logs_root` declared in `config/data_paths.yaml`."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "data_paths.yaml").write_text("logs_root: custom_logs\n", encoding="utf-8")

    setup_logging(to_file=True)

    expected_log_file = tmp_path / "custom_logs" / "app.log"
    assert expected_log_file.exists()
    file_handlers = [h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1
    assert Path(file_handlers[0].baseFilename) == expected_log_file.resolve()


def test_setup_logging_to_file_false_adds_no_file_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`to_file=False` configures only a stream handler, never touching the filesystem."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")

    setup_logging(to_file=False)

    handlers = logging.getLogger().handlers
    assert all(not isinstance(h, logging.FileHandler) for h in handlers)
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)
    assert not (tmp_path / "logs").exists()


def test_logs_dir_falls_back_to_default_when_config_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing `config/data_paths.yaml` falls back to `<repo_root>/logs` rather than erroring."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")

    assert _logging_setup_mod._logs_dir() == tmp_path / "logs"


def test_logs_dir_falls_back_to_default_when_logs_root_key_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A present config without a `logs_root` key still falls back to `<repo_root>/logs`."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "data_paths.yaml").write_text("data_root: data\n", encoding="utf-8")

    assert _logging_setup_mod._logs_dir() == tmp_path / "logs"


@pytest.mark.parametrize(
    ("config_text", "expected_exception"),
    [
        pytest.param("- just\n- a\n- list\n", TypeError, id="non_mapping_top_level"),
        pytest.param("logs_root:\n", ValueError, id="null_logs_root_value"),
        pytest.param(": not valid yaml : at all :\n", yaml.YAMLError, id="unparsable_yaml"),
    ],
)
def test_logs_dir_raises_on_invalid_config_rather_than_silently_falling_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config_text: str, expected_exception: type[Exception]
) -> None:
    """A present but malformed config fails loudly instead of writing logs somewhere unexpected."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "data_paths.yaml").write_text(config_text, encoding="utf-8")

    with pytest.raises(expected_exception):
        _logging_setup_mod._logs_dir()


def test_setup_logging_raises_on_unrecognized_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrecognized level name raises instead of silently falling back to INFO."""
    monkeypatch.setattr(_logging_setup_mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(_logging_setup_mod, "_DATA_PATHS_CONFIG", tmp_path / "config" / "data_paths.yaml")

    with pytest.raises(ValueError, match="unrecognized logging level"):
        setup_logging(level="DEBG", to_file=False)
