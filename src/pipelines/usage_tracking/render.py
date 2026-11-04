"""Markdown renderer for the daily usage report. Pure: takes the merged day models and returns a string; the CLI writes the file.

Tables go through `MarkdownTableRenderer`, which satisfies `src.lib.report_render.protocols.ReportRenderer` (rows of strings). `render_report` itself is a plain function because it carries no
state and takes the domain models rather than string rows.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .athena_source import SessionRow
from .merge import Flag, HouseholdDay, PersonDay, trend_days

DEVICE_CHARS = 8
HHID_CHARS = 6
NONE = "-"


class MarkdownTableRenderer:
    """Renders a list of same-keyed string rows as a GitHub Markdown table; the first row's keys are the header."""

    def render(self, rows: list[dict[str, str]]) -> str:
        if not rows:
            return ""
        header = list(rows[0])
        lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
        lines += ["| " + " | ".join(_cell(row[h]) for h in header) + " |" for row in rows]
        return "\n".join(lines)


_TABLE = MarkdownTableRenderer()


def render_report(tenant: str, day: date, households: Sequence[HouseholdDay]) -> str:
    """One report per tenant. `households` must all belong to `tenant`; every section is always rendered."""
    sections = [f"# Household usage report - {tenant} - {day}", _summary(households)]
    sections += [_household(hd) for hd in households]
    sections += [_anomalies(households), _trend(households, day)]
    return "\n\n".join(sections) + "\n"


def _summary(households: Sequence[HouseholdDay]) -> str:
    people = [p for hd in households for p in hd.people]
    return (
        f"**Summary:** {len(households)} HHIDs, {len(people)} devices, {sum(p.active for p in people)} active, "
        f"{sum(p.sessions for p in people)} sessions, {sum(p.errors for p in people)} errors."
    )


def _household(hd: HouseholdDay) -> str:
    rows = [_person_row(p) for p in hd.people]
    parts = [f"## {hd.household.label} ({_short_hhid(hd.household.hhid)})", _TABLE.render(rows)]
    for person in hd.people:
        sessions = [s for s in hd.sessions if s.device_id == person.device_id]
        if sessions:
            parts += [f"### {person.name} - sessions", _TABLE.render([_session_row(s, hd) for s in sorted(sessions, key=lambda s: s.event_start)])]
    return "\n\n".join(parts)


def _person_row(p: PersonDay) -> dict[str, str]:
    return {
        "Person": p.name,
        "Device": p.device_id[:DEVICE_CHARS],
        "Active": "yes" if p.active else "no",
        "Sessions": str(p.sessions),
        "Watch min": f"{p.watch_minutes:.1f}",
        "Errors": str(p.errors),
        "Top content": p.top_content or NONE,
        "Lightstep reqs": str(p.lightstep_requests),
        "Flags": ", ".join(sorted({f.kind for f in p.flags})) or NONE,
    }


def _session_row(s: SessionRow, hd: HouseholdDay) -> dict[str, str]:
    errors = [e for e in hd.errors if e.session_id == s.session_id]
    traces = hd.lightstep_traces.get(s.session_id, ())
    return {
        "Time": s.event_start[11:19] or NONE,
        "parent_session_id": s.session_id,
        "Content": s.content or NONE,
        "Endreason": s.outcome or NONE,
        "Error": "; ".join(f"{e.error_code} {e.message}".strip() for e in errors) or NONE,
        "trace_id": traces[0] + (f" (+{len(traces) - 1})" if len(traces) > 1 else "") if traces else NONE,
    }


def _anomalies(households: Sequence[HouseholdDay]) -> str:
    lines = [f"- {hd.household.label} `{hd.household.hhid}`: {_describe(f)}" for hd in households for f in hd.flags]
    return "## Anomalies\n\n" + ("\n".join(lines) if lines else "None.")


def _describe(flag: Flag) -> str:
    device = f" device `{flag.device_id}`" if flag.device_id else ""
    return f"**{flag.kind}**{device} - {flag.detail}"


def _trend(households: Sequence[HouseholdDay], day: date) -> str:
    days = [d.strftime("%m-%d") for d in trend_days(day)]
    rows = [
        {"Household": hd.household.label, "Person": p.name, **{d: str(n) for d, n in zip(days, p.trend)}}
        for hd in households
        for p in hd.people
    ]
    return "## 7-day trend (sessions per day)\n\n" + (_TABLE.render(rows) if rows else "No tracked households.")


def _short_hhid(hhid: str) -> str:
    return hhid[:HHID_CHARS] + "…" if len(hhid) > HHID_CHARS else hhid


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
