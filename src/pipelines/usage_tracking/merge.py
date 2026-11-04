"""Pure merge of Athena and Lightstep rows into a per-household, per-day model. No I/O: inputs are plain rows, outputs are frozen dataclasses."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .athena_source import DeviceSeen, ErrorRow, SessionRow, errored_sessions
from .errors import MergeError
from .lightstep_source import RequestRow, request_counts
from .roster import Household, Member

TREND_DAYS = 7


@dataclass(frozen=True)
class Flag:
    kind: str
    device_id: str | None
    detail: str


@dataclass(frozen=True)
class PersonDay:
    name: str
    device_id: str
    active: bool
    sessions: int
    watch_minutes: float
    errors: int
    top_content: str | None
    lightstep_requests: int
    trend: tuple[int, ...]
    flags: tuple[Flag, ...] = ()


@dataclass(frozen=True)
class HouseholdDay:
    household: Household
    day: date
    people: tuple[PersonDay, ...]
    sessions: tuple[SessionRow, ...]
    errors: tuple[ErrorRow, ...]
    new_devices: tuple[DeviceSeen, ...]
    athena_session_ids: frozenset[str]
    window_session_ids: frozenset[str]
    lightstep_session_devices: Mapping[str, str]
    flags: tuple[Flag, ...] = ()
    lightstep_traces: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


def trend_days(day: date) -> list[date]:
    """The trailing `TREND_DAYS` days ending on `day`, oldest first."""
    return [day - timedelta(days=offset) for offset in range(TREND_DAYS - 1, -1, -1)]


def build_trend(sessions: Iterable[SessionRow], household: Household, day: date) -> dict[str, tuple[int, ...]]:
    """Sessions per member device per day over one Athena window; days with no sessions are 0."""
    window = trend_days(day)
    counts: Counter[tuple[str, date]] = Counter()
    for s in sessions:
        started = _start_day(s.event_start)
        if s.household_id == household.hhid and started in window:
            counts[(s.device_id, started)] += 1
    return {m.device_id: tuple(counts[(m.device_id, d)] for d in window) for m in household.members}


def build_household_day(
    household: Household,
    day: date,
    window_sessions: Sequence[SessionRow],
    devices_seen: Iterable[DeviceSeen],
    errors: Iterable[ErrorRow],
    requests: Sequence[RequestRow],
) -> HouseholdDay:
    """`window_sessions` must cover the trailing `TREND_DAYS` days ending on `day` (one Athena window); the report day's sessions are filtered out of it."""
    member_ids = {m.device_id for m in household.members}
    today = tuple(s for s in window_sessions if s.household_id == household.hhid and s.device_id in member_ids and _start_day(s.event_start) == day)
    trend = build_trend(window_sessions, household, day)
    lightstep = request_counts(requests, [household])
    people = tuple(_person(m, lightstep.get((household.hhid, m.device_id), 0), today, trend[m.device_id]) for m in household.members)
    session_ids = {s.session_id for s in today if s.session_id}
    window_ids = {s.session_id for s in window_sessions if s.household_id == household.hhid and s.device_id in member_ids and s.session_id}
    kept_errors = tuple(e for e in errors if e.session_id in session_ids)
    new = tuple(d for d in devices_seen if d.household_id == household.hhid and d.device_id not in member_ids)
    lightstep_devices = {r.session_id: r.device_id for r in requests if r.household_id == household.hhid and r.device_id in member_ids and r.session_id}
    traces: dict[str, set[str]] = {}
    for r in requests:
        if r.household_id == household.hhid and r.device_id in member_ids and r.session_id and r.trace_id:
            traces.setdefault(r.session_id, set()).add(r.trace_id)
    return HouseholdDay(
        household, day, people, today, kept_errors, new, frozenset(session_ids), frozenset(window_ids), lightstep_devices,
        lightstep_traces={sid: tuple(sorted(t)) for sid, t in traces.items()},
    )


def _person(member: Member, lightstep_requests: int, sessions: Sequence[SessionRow], trend: tuple[int, ...]) -> PersonDay:
    mine = [s for s in sessions if s.device_id == member.device_id]
    content = Counter(s.content for s in mine if s.content)
    return PersonDay(
        name=member.name,
        device_id=member.device_id,
        active=bool(mine),
        sessions=len(mine),
        watch_minutes=round(sum(_minutes(s) for s in mine), 1),
        errors=len(errored_sessions(mine)),
        top_content=content.most_common(1)[0][0] if content else None,
        lightstep_requests=lightstep_requests,
        trend=trend,
    )


def _minutes(session: SessionRow) -> float:
    start, end = _parse(session.event_start), _parse(session.event_end)
    if start is None or end is None:
        return 0.0
    return max((end - start).total_seconds(), 0.0) / 60


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value[:19].replace("T", " "))
    except ValueError:
        return None


def _start_day(value: str) -> date:
    parsed = _parse(value)
    if parsed is None:
        raise MergeError(f"session has an unparseable event_start: {value!r}")
    return parsed.date()
