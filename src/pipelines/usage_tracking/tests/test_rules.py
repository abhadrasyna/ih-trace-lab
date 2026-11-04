"""Tests for the flag rules (no network)."""
from __future__ import annotations

from datetime import date

from src.pipelines.usage_tracking.athena_source import SessionRow
from src.pipelines.usage_tracking.merge import Flag, build_household_day
from src.pipelines.usage_tracking.roster import Household, Member
from src.pipelines.usage_tracking.rules import RULES, apply_rules, idle_rule

DAY = date(2026, 11, 2)


def _hh(active_from: str | None) -> Household:
    return Household(hhid="H1", label="t", tenant="ZA", track=True, members=(Member("Sai", "d1", active_from),))


def test_idle_skipped_before_active_from():
    hd = build_household_day(_hh("2026-11-05"), DAY, [], [], [], [])
    assert idle_rule(hd) == []
    assert idle_rule(build_household_day(_hh("2026-11-01"), DAY, [], [], [], [])) == []
    assert [f.kind for f in idle_rule(build_household_day(_hh("2026-10-31"), DAY, [], [], [], []))] == ["idle"]


def test_new_rule_is_picked_up_by_apply_rules():
    hd = build_household_day(_hh(None), DAY, [SessionRow("s1", "H1", "d1", "c", "", "DESTROY", "2026-11-02 10:00:00", "")], [], [], [])

    def custom(_hd):
        return [Flag("custom", "d1", "x")]

    out = apply_rules(hd, [*RULES, custom])
    assert [f.kind for f in out.people[0].flags] == ["mismatch", "custom"]
