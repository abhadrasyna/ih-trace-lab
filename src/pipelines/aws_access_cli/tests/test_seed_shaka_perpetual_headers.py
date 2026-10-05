"""Tests for `seed_shaka_perpetual_headers.py`'s legacy-header migration helper."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.pipelines.aws_access_cli.scripts.seed_shaka_perpetual_headers import seed_headers


def _write_legacy_header(path: Path, header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(header)


def test_seeds_new_file_with_legacy_header_order(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    output_root = tmp_path / "new"
    legacy_header = ["session_date", "1001", "E31012", "ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT", "1006"]
    _write_legacy_header(legacy_root / "ZA" / "weekly" / "shaka_error_hhid.csv", legacy_header)

    actions = seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)

    seeded_path = output_root / "ZA" / "weekly" / "shaka-error-hhid.csv"
    assert seeded_path.is_file()
    with seeded_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows == [legacy_header]
    assert any("SEEDED" in action and "ZA/weekly/shaka-error-hhid" in action for action in actions)


def test_skips_when_new_repo_file_already_exists(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    output_root = tmp_path / "new"
    _write_legacy_header(legacy_root / "ZA" / "weekly" / "shaka_error_hhid.csv", ["session_date", "1006", "E31012"])
    existing_header = ["session_date", "1001", "E31012"]
    _write_legacy_header(output_root / "ZA" / "weekly" / "shaka-error-hhid.csv", existing_header)

    seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)

    with (output_root / "ZA" / "weekly" / "shaka-error-hhid.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows == [existing_header]


def test_skips_when_no_legacy_file(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    output_root = tmp_path / "new"

    actions = seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)

    assert not (output_root / "ZA" / "weekly" / "shaka-error-hhid.csv").is_file()
    assert any("SKIP  (no legacy file)" in action for action in actions)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    output_root = tmp_path / "new"
    _write_legacy_header(legacy_root / "ZA" / "monthly" / "shaka_error_sessions.csv", ["session_date", "1006"])

    actions = seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=True)

    assert not (output_root / "ZA" / "monthly" / "shaka-error-session.csv").is_file()
    assert any("WOULD SEED" in action for action in actions)


def test_raises_if_legacy_root_does_not_exist(tmp_path: Path) -> None:
    missing_legacy_root = tmp_path / "does-not-exist"
    output_root = tmp_path / "new"

    with pytest.raises(NotADirectoryError):
        seed_headers(legacy_root=missing_legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)


def test_strips_bom_from_legacy_header(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    output_root = tmp_path / "new"
    legacy_path = legacy_root / "ZA" / "weekly" / "shaka_error_hhid.csv"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_bytes("session_date,1001,E31012\n".encode("utf-8-sig"))

    seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)

    with (output_root / "ZA" / "weekly" / "shaka-error-hhid.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "session_date"


def test_skips_legacy_file_with_blank_first_line(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    output_root = tmp_path / "new"
    legacy_path = legacy_root / "ZA" / "weekly" / "shaka_error_hhid.csv"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("\n", encoding="utf-8")

    actions = seed_headers(legacy_root=legacy_root, output_root=output_root, tenant_codes=["ZA"], dry_run=False)

    assert not (output_root / "ZA" / "weekly" / "shaka-error-hhid.csv").is_file()
    assert any("SKIP  (no legacy file)" in action for action in actions)
