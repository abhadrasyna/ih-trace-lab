"""Tests for the tracked-household roster loader (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipelines.usage_tracking import roster
from src.pipelines.usage_tracking.errors import RosterError, UsageTrackingError

VALID = """
tenant: ZA
households:
  - hhid: H1
    label: team
    track: true
    phone: "600000001"
    members:
      - {name: Sai, device_id: d1, active_from: 2026-11-04}
      - {name: Fayaz, device_id: d2}
  - hhid: H2
    track: false
    members: []
"""


def _write(tmp_path: Path, text: str, name: str = "roster.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_valid_roster_and_filters_untracked(tmp_path: Path) -> None:
    loaded = roster.load(_write(tmp_path, VALID))

    assert loaded.tenant == "ZA"
    assert len(loaded.households) == 2
    assert [h.hhid for h in roster.tracked(loaded)] == ["H1"]
    assert loaded.households[0].members[0].active_from == "2026-11-04"
    assert loaded.households[0].members[1].active_from is None
    assert loaded.households[0].phone == "600000001"
    assert loaded.households[1].phone is None


def test_duplicate_device_id_raises(tmp_path: Path) -> None:
    text = VALID.replace("device_id: d2", "device_id: d1")

    with pytest.raises(RosterError, match="duplicate device_id d1"):
        roster.load(_write(tmp_path, text))


def test_unknown_tenant_raises(tmp_path: Path) -> None:
    with pytest.raises(RosterError, match="unknown tenant 'XX'"):
        roster.load(_write(tmp_path, VALID.replace("tenant: ZA", "tenant: XX")))


def test_json_config_loads(tmp_path: Path) -> None:
    data = {"tenant": "ZA", "households": [{"hhid": "H1", "track": True, "phone": "600000001", "members": [{"name": "Sai", "device_id": "d1"}]}]}

    loaded = roster.load(_write(tmp_path, json.dumps(data), "roster.json"))

    assert roster.tracked(loaded)[0].members[0].device_id == "d1"


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("hhid: H1", "hhid: ''", "empty or missing hhid"),
        ("track: true", "track: yes-please", "'track' must be true or false"),
        ("{name: Fayaz, device_id: d2}", "{name: Fayaz}", "member without a device_id"),
        ("active_from: 2026-11-04", "active_from: 20261104", "invalid active_from"),
        ("members: []", "members: {}", "'members' must be a list"),
        ('    phone: "600000001"\n', "", "needs a phone"),
        ('phone: "600000001"', "phone: 600000001", "'phone' must be a non-empty quoted string"),
        ("      - {name: Sai, device_id: d1, active_from: 2026-11-04}\n      - {name: Fayaz, device_id: d2}\n", "", "at least one member"),
    ],
)
def test_malformed_entries_raise(tmp_path: Path, old: str, new: str, message: str) -> None:
    with pytest.raises(RosterError, match=message):
        roster.load(_write(tmp_path, VALID.replace(old, new)))


def test_duplicate_hhid_raises(tmp_path: Path) -> None:
    with pytest.raises(RosterError, match="duplicate hhid H1"):
        roster.load(_write(tmp_path, VALID.replace("hhid: H2", "hhid: H1")))


def test_non_utf8_file_raises_roster_error(tmp_path: Path) -> None:
    path = tmp_path / "roster.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")

    with pytest.raises(RosterError, match="cannot read roster"):
        roster.load(path)


def test_missing_file_raises_roster_error(tmp_path: Path) -> None:
    with pytest.raises(UsageTrackingError, match="cannot read roster"):
        roster.load(tmp_path / "absent.yaml")


def test_config_path_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(roster.CONFIG_ENV_VAR, raising=False)
    assert roster.resolve_config_path() == roster.DEFAULT_CONFIG

    monkeypatch.setenv(roster.CONFIG_ENV_VAR, "/tmp/env.yaml")
    assert roster.resolve_config_path() == Path("/tmp/env.yaml")
    assert roster.resolve_config_path("/tmp/cli.yaml") == Path("/tmp/cli.yaml")


def test_committed_roster_is_valid() -> None:
    loaded = roster.load(roster.DEFAULT_CONFIG)

    assert roster.tracked(loaded)
    assert all(h.members for h in roster.tracked(loaded))
