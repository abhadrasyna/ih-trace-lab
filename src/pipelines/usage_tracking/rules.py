"""Flag rules for the usage report: one function per flag, collected in `RULES`. Adding a flag means adding a function and appending it here."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, timedelta

from .athena_source import errored_sessions
from .merge import Flag, HouseholdDay, PersonDay

IDLE_DAYS = 3

Rule = Callable[[HouseholdDay], list[Flag]]


def idle_rule(hd: HouseholdDay) -> list[Flag]:
    flags = []
    for member, person in zip(hd.household.members, hd.people):
        if _covers_idle_window(member.active_from, hd.day) and sum(person.trend[-IDLE_DAYS:]) == 0:
            flags.append(Flag("idle", person.device_id, f"no sessions in the last {IDLE_DAYS} days"))
    return flags


def error_endreason_rule(hd: HouseholdDay) -> list[Flag]:
    codes: dict[str, str] = {}
    for e in hd.errors:
        codes[e.session_id] = f"{codes[e.session_id]}, {e.error_code}" if e.session_id in codes else e.error_code
    return [
        Flag("error_endreason", s.device_id, f"{s.session_id} ended {s.outcome}" + (f" (code {codes[s.session_id]})" if s.session_id in codes else ""))
        for s in errored_sessions(hd.sessions)
    ]


def mismatch_rule(hd: HouseholdDay) -> list[Flag]:
    devices = {s.session_id: s.device_id for s in hd.sessions}
    lightstep = hd.lightstep_session_devices
    flags = [Flag("mismatch", devices[sid], f"{sid} in Athena only") for sid in sorted(hd.athena_session_ids - lightstep.keys())]
    flags += [Flag("mismatch", lightstep[sid], f"{sid} in Lightstep only") for sid in sorted(lightstep.keys() - hd.window_session_ids)]
    return flags


def new_device_rule(hd: HouseholdDay) -> list[Flag]:
    if not hd.household.track:
        return []
    return [Flag("new_device", d.device_id, f"not in roster; first seen {d.first_seen}, {d.session_count} sessions") for d in hd.new_devices]


RULES: list[Rule] = [idle_rule, error_endreason_rule, mismatch_rule, new_device_rule]


def apply_rules(hd: HouseholdDay, rules: Sequence[Rule] = RULES) -> HouseholdDay:
    """Return `hd` with household-level flags set and each person's flags filled by device id."""
    flags = tuple(f for rule in rules for f in rule(hd))
    people = tuple(replace(p, flags=_for_device(flags, p)) for p in hd.people)
    return replace(hd, people=people, flags=flags)


def _for_device(flags: Sequence[Flag], person: PersonDay) -> tuple[Flag, ...]:
    return tuple(f for f in flags if f.device_id == person.device_id)


def _covers_idle_window(active_from: str | None, day: date) -> bool:
    return active_from is None or date.fromisoformat(active_from) <= day - timedelta(days=IDLE_DAYS - 1)
