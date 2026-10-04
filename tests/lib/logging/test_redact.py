"""Tests for ``src.lib.logging.redact``."""

from __future__ import annotations

import pytest

from src.lib.logging.redact import redact_params


def test_redact_params_masks_non_allowed_keys() -> None:
    assert redact_params(
        {"tenant": "mtn-za", "sql": "select 1", "password": "secret"},
        {"tenant"},
    ) == {"tenant": "mtn-za", "sql": "***", "password": "***"}


def test_redact_params_empty_allow_keys_raises() -> None:
    with pytest.raises(ValueError, match="allow_keys must not be empty"):
        redact_params({"a": 1}, set())
