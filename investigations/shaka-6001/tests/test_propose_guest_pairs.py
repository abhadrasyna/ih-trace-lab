"""Offline tests for propose_guest_pairs (synthetic Lightstep series only)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "propose_guest_pairs.py"
spec = importlib.util.spec_from_file_location("propose_guest_pairs", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

MIN = 60_000
T0 = 1_793_938_200_000


def _series(ip, device, hhid, guest, points, ua=""):
    labels = [f"http.client_ip={ip}", f"sessionInfo.deviceId={device}", f"sessionInfo.householdId={hhid}",
              f"sessionInfo.guestMode={guest}", f"http.user_agent={ua}"]
    return {"group-labels": labels, "points": [[T0 + m * MIN, n] for m, n in points]}


def test_unique_pair_on_same_ip_within_gap():
    series = [
        _series("1.1.1.1", "g-dev", "g-dev", "1", [(0, 1), (1, 3)], ua="UA"),
        _series("1.1.1.1", "r-dev", "R-HH", "0", [(3, 2), (4, 5)], ua="UA"),
    ]
    rows = mod.pair_identities(mod.parse_identities(series), max_gap_s=600)
    assert len(rows) == 1
    assert (rows[0]["real_device"], rows[0]["real_hhid"], rows[0]["gap_s"]) == ("r-dev", "R-HH", 120)
    assert (rows[0]["ua_match"], rows[0]["confidence"]) == ("yes", "unique")


def test_shared_ip_is_ambiguous_and_other_ip_or_order_is_excluded():
    series = [
        _series("1.1.1.1", "g", "g", "1", [(0, 1)]),
        _series("1.1.1.1", "r1", "H1", "0", [(2, 1)]),
        _series("1.1.1.1", "r2", "H2", "0", [(3, 1)]),
        _series("2.2.2.2", "r3", "H3", "0", [(2, 1)]),
        _series("1.1.1.1", "early", "H4", "0", [(-5, 1)]),
        _series("1.1.1.1", "late", "H5", "0", [(60, 1)]),
    ]
    rows = mod.pair_identities(mod.parse_identities(series), max_gap_s=600)
    assert {r["real_device"] for r in rows} == {"r1", "r2"}
    assert {r["confidence"] for r in rows} == {"ambiguous"}


def test_build_uql_rejects_unknown_shared_filter_key():
    assert 'sessionInfo.busUnitId == "x"' in mod.build_uql(["1.1.1.1"], {"sessionInfo.busUnitId": "x"})
    with pytest.raises(ValueError):
        mod.build_uql(["1.1.1.1"], {"other": "x"})


def test_user_agent_mismatch_is_not_unique():
    series = [_series("1.1.1.1", "g", "g", "1", [(0, 1)], ua="A"), _series("1.1.1.1", "r", "H", "0", [(2, 1)], ua="B")]
    rows = mod.pair_identities(mod.parse_identities(series), max_gap_s=600)
    assert rows[0]["confidence"] == "ua_mismatch"
