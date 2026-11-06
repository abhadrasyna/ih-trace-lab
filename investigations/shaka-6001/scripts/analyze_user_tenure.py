"""How long have active households been around, are they sticky, and does playback success differ by tenure?

Everything is derived from the local ``<date>_session.csv`` playback-outcome files (no Athena, no new query), read
through ``scripts.lib.local_data`` from every configured source, so ``ctap-smvod`` history is picked up too. The
tenure proxy is **first seen** (the household's earliest session date in IST), never a subscription date. The local
history starts at ``--history-start`` (default 2026-10-01), so tenure is capped at the history length and every
household first seen on the earliest retained date is *left-censored* (its true tenure is longer, unknown): it carries
``censored=True`` and the 91-180d and 180d+ buckets stay in the output at zero rather than disappearing. Every output
carries ``earliest_retained_date`` and a limits note saying so.

Active household: at least one session on or after ``--active-since`` (default 2026-10-01); first seen is measured
over the whole retained history. With the default history start every local household qualifies. Tenure is days from
first seen to ``--end-date`` (IST dates). Buckets: 0-7d, 8-30d, 31-90d, 91-180d, 180d+ (181 and more).

Success: ``src.lib.playback.is_success`` (``DESTROY``) over sessions with a playback attempt (a non-blank
``playback_outcome``); a session id seen twice counts once. Bucket success is computed over the retained history up to
``--end-date``, with the household's tenure at ``--end-date``. 6001 households and rates come from the SU-10 cohort for
``--start-date/--end-date`` (``<start>_<end>_6001_cohort.csv``) when it exists; the base is the bucket's households
with a session in that range. Without the cohort those columns stay empty and the notes say so. The before/after
tenure split uses the period of a household's *first* 6001 (cohort) versus no 6001 in the range.

Rows with no ``event_start`` (about half, mostly failed sessions) are kept and dated by their file's day, so success is
not biased upwards; they get no period. The count is in the notes.

Stickiness: share active on 7 or more distinct days and in more than one ISO week; first-seen-week cohorts and how many
were active in a later week or in the last 7 days. The first week is partial (history starts mid-week).
``GUEST.*`` ids are per-install, not households: they are excluded from tenure, buckets and stickiness and reported on
their own ``cohort=guest`` row. Per-day row counts are written and small days (below ``--small-day-fraction`` of the
median day) are flagged because a partial day biases first seen towards later dates. Timestamps are UTC, converted to
IST for every day or period decision. Rerunning overwrites the outputs; a chart failure never blocks the CSVs.
"""

from __future__ import annotations

import argparse
import logging
import os
import statistics
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.build_6001_cohort import GUEST_PREFIX, IST, SESSION_ARTIFACT, _parse_utc  # noqa: E402
from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, load_daily  # noqa: E402
from scripts.lib.period import classify_period  # noqa: E402
from src.lib.charts.composition import Part, render_composition  # noqa: E402
from src.lib.charts.errors import ChartError  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402
from src.lib.charts.rate_bars import RateRow, render_rate_bars  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.playback import is_success  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_user_tenure")
COHORT_ARTIFACT = "6001_cohort"
HOUSEHOLDS_ARTIFACT = "user_tenure_households"
BUCKETS_ARTIFACT = "user_tenure_buckets"
STICKINESS_ARTIFACT = "user_tenure_stickiness"
SIX_ARTIFACT = "user_tenure_6001"
ROWCOUNT_ARTIFACT = "user_tenure_row_counts"
DEFAULT_HISTORY_START = date(2026, 10, 1)
FILE_DATE_KEY = "_file_date"
BASE = "households (sessions for success rates); first seen from local session files"
COHORT_HOUSEHOLD = "household"
COHORT_GUEST = "guest"
BUCKETS = ("0-7d", "8-30d", "31-90d", "91-180d", "180d+")
_BUCKET_UPPER = (7, 30, 90, 180)
WEEK_DAYS = 7
MIN_ACTIVE_DAYS = 7
REQUIRED_SESSION_COLUMNS = ("householdId", "deviceId", "playback_outcome", "event_start")
REQUIRED_COHORT_COLUMNS = ("household_id", "is_guest", "period")
HOUSEHOLD_FIELDS = [
    "tenant", "household_id", "first_seen", "last_seen", "tenure_days", "bucket", "censored", "active_days",
    "active_weeks", "sessions", "attempts", "successes", "success_rate", "has_6001", "first_6001_period",
    "earliest_retained_date", "limits_note",
]
BUCKET_FIELDS = [
    "tenant", "base", "cohort", "bucket", "households", "share", "censored_households", "censored_share",
    "sessions", "attempts", "successes", "success_rate", "active_7plus_days", "active_7plus_rate",
    "multi_week", "multi_week_rate", "households_in_range", "households_6001", "rate_6001",
    "earliest_retained_date", "limits_note",
]
STICKINESS_FIELDS = [
    "tenant", "base", "view", "group", "households", "censored_households", "active_7plus_days",
    "active_7plus_rate", "multi_week", "multi_week_rate", "active_later_week", "active_later_week_rate",
    "active_last_7d", "active_last_7d_rate", "earliest_retained_date", "limits_note",
]
SIX_FIELDS = [
    "tenant", "base", "period", "has_6001", "households", "median_tenure_days", "mean_tenure_days",
    "censored_households", "censored_share", "earliest_retained_date", "limits_note",
]
ROWCOUNT_FIELDS = ["tenant", "file_date_utc", "session_rows", "small_day", "median_rows", "earliest_retained_date",
                   "limits_note"]


class TenureError(Exception):
    """Raised for missing or malformed inputs."""


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    household_id: str
    device_id: str
    outcome: str
    start_ist: date
    start_utc: datetime | None  # None: dated by its file's day instead


@dataclass
class HouseholdStats:
    household_id: str
    dates: set[date] = field(default_factory=set)
    sessions: int = 0
    attempts: int = 0
    successes: int = 0


@dataclass(frozen=True)
class Aggregation:
    households: dict[str, HouseholdStats]
    guests: HouseholdStats
    untimed_sessions: int
    file_dated_sessions: int
    outside_range_sessions: int
    no_household_sessions: int
    guest_ids: int
    sessions: list[SessionRecord]


def bucket_for(tenure_days: int) -> str:
    """0-7d, 8-30d, 31-90d, 91-180d, 180d+ (181 and up); a negative tenure is a bug, not a bucket."""
    if tenure_days < 0:
        raise TenureError(f"negative tenure: {tenure_days}")
    for label, upper in zip(BUCKETS, _BUCKET_UPPER):
        if tenure_days <= upper:
            return label
    return BUCKETS[-1]


def is_guest_id(household_id: str, device_id: str = "") -> bool:
    return household_id.startswith(GUEST_PREFIX) or device_id.startswith(GUEST_PREFIX)


def limits_note(earliest: date, tenant: str) -> str:
    return (f"first seen, not a subscription date; left-censored at {earliest.isoformat()} "
            f"(local history only, tenant {tenant}); 91-180d and 180d+ are capped by history length")


def read_sessions(rows: Iterable[Mapping[str, str]]) -> list[SessionRecord | None]:
    """Parse playback-outcome rows.

    About half the real rows (mostly failures: EBVS, INCOMPLETE_NO_DESTROY, ...) have no ``event_start``; dropping
    them would bias success upwards, so they are dated by the day of the file they came from (``FILE_DATE_KEY``,
    treated as an IST day; no period can be assigned to them). A row with neither yields None and is counted.
    """
    out: list[SessionRecord | None] = []
    for row in rows:
        missing = [c for c in REQUIRED_SESSION_COLUMNS if c not in row]
        if missing:
            raise TenureError(f"session rows lack columns {missing}; not playback-outcome data")
        start = _parse_utc(row.get("event_start") or "")
        day = start.astimezone(IST).date() if start else _file_day(row)
        out.append(None if day is None else SessionRecord(
            (row.get("sessionId") or "").strip(), (row.get("householdId") or "").strip(),
            (row.get("deviceId") or "").strip(), (row.get("playback_outcome") or "").strip(), day, start))
    return out


def _file_day(row: Mapping[str, str]) -> date | None:
    try:
        return date.fromisoformat(row[FILE_DATE_KEY])
    except (KeyError, ValueError):
        return None


def aggregate(records: Iterable[SessionRecord | None], active_since: date, end_date: date) -> Aggregation:
    """Per-household session dates and counts. Guests are tallied apart from households and never get tenure.

    A session id seen twice counts once. Sessions dated after ``end_date`` (IST) are counted and dropped; the
    active-since filter is applied after first seen is known, in :func:`build_households`.
    """
    households: dict[str, HouseholdStats] = {}
    guests = HouseholdStats("GUEST.*")
    guest_ids: set[str] = set()
    seen: set[str] = set()
    kept: list[SessionRecord] = []
    untimed = outside = no_household = file_dated = 0
    for rec in records:
        if rec is None:
            untimed += 1
            continue
        if rec.session_id and rec.session_id in seen:
            continue
        seen.add(rec.session_id)
        if rec.start_ist > end_date:
            outside += 1
            continue
        kept.append(rec)
        file_dated += rec.start_utc is None
        guest = is_guest_id(rec.household_id, rec.device_id)
        if not guest and not rec.household_id:
            no_household += 1
            continue
        stats = guests if guest else households.setdefault(rec.household_id, HouseholdStats(rec.household_id))
        if guest:
            guest_ids.add(rec.household_id or rec.device_id)
        stats.dates.add(rec.start_ist)
        stats.sessions += 1
        stats.attempts += bool(rec.outcome)
        stats.successes += is_success(rec.outcome)
    return Aggregation(households, guests, untimed, file_dated, outside, no_household, len(guest_ids), kept)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def build_households(agg: Aggregation, *, active_since: date, end_date: date, earliest: date, tenant: str,
                     cohort: Mapping[str, str] | None = None) -> list[dict]:
    """One row per active, non-guest household. ``cohort`` maps household id -> period of its first 6001."""
    rows: list[dict] = []
    note = limits_note(earliest, tenant)
    for stats in agg.households.values():
        if max(stats.dates) < active_since:
            continue
        first, last = min(stats.dates), max(stats.dates)
        tenure = (end_date - first).days
        rows.append({
            "tenant": tenant, "household_id": stats.household_id, "first_seen": first.isoformat(),
            "last_seen": last.isoformat(), "tenure_days": tenure, "bucket": bucket_for(tenure),
            "censored": first <= earliest, "active_days": len(stats.dates),
            "active_weeks": len({_week_start(d) for d in stats.dates}), "sessions": stats.sessions,
            "attempts": stats.attempts, "successes": stats.successes, "success_rate": _rate(stats.successes, stats.attempts),
            "has_6001": "" if cohort is None else stats.household_id in cohort,
            "first_6001_period": "" if cohort is None else cohort.get(stats.household_id, ""),
            "earliest_retained_date": earliest.isoformat(), "limits_note": note,
        })
    return sorted(rows, key=lambda r: (r["first_seen"], r["household_id"]))


def _rate(count: int, base: int) -> float | str:
    return round(count / base, 6) if base else ""


def _stick(rows: Sequence[dict], end_date: date, stats: Mapping[str, HouseholdStats]) -> dict:
    n = len(rows)
    seven = sum(r["active_days"] >= MIN_ACTIVE_DAYS for r in rows)
    multi = sum(r["active_weeks"] > 1 for r in rows)
    later = recent = 0
    for r in rows:
        dates = stats[r["household_id"]].dates
        first_week = _week_start(date.fromisoformat(r["first_seen"]))
        later += any(_week_start(d) > first_week for d in dates)
        recent += max(dates) >= end_date - timedelta(days=WEEK_DAYS - 1)
    return {"households": n, "censored_households": sum(bool(r["censored"]) for r in rows),
            "active_7plus_days": seven, "active_7plus_rate": _rate(seven, n),
            "multi_week": multi, "multi_week_rate": _rate(multi, n),
            "active_later_week": later, "active_later_week_rate": _rate(later, n),
            "active_last_7d": recent, "active_last_7d_rate": _rate(recent, n)}


def summarise_stickiness(rows: Sequence[dict], agg: Aggregation, end_date: date, tenant: str, earliest: date) -> list[dict]:
    """Stickiness overall, per tenure bucket and per first-seen ISO week (Monday label)."""
    common = {"tenant": tenant, "base": "households", "earliest_retained_date": earliest.isoformat(),
              "limits_note": limits_note(earliest, tenant)}
    views: list[tuple[str, str, list[dict]]] = [("overall", "all", list(rows))]
    views += [("bucket", b, [r for r in rows if r["bucket"] == b]) for b in BUCKETS]
    weeks: dict[date, list[dict]] = defaultdict(list)
    for r in rows:
        weeks[_week_start(date.fromisoformat(r["first_seen"]))].append(r)
    views += [("first_seen_week", w.isoformat(), weeks[w]) for w in sorted(weeks)]
    return [{**common, "view": v, "group": g, **_stick(members, end_date, agg.households)} for v, g, members in views]


def summarise_buckets(rows: Sequence[dict], agg: Aggregation, end_date: date, tenant: str, earliest: date, *,
                      cohort_ids: set[str] | None, in_range: set[str]) -> list[dict]:
    """Per bucket households, share, censoring, success, stickiness and (cohort present) 6001; plus the guest row."""
    common = {"tenant": tenant, "base": BASE, "earliest_retained_date": earliest.isoformat(),
              "limits_note": limits_note(earliest, tenant)}
    total = len(rows)
    out: list[dict] = []
    for bucket in BUCKETS:
        members = [r for r in rows if r["bucket"] == bucket]
        n = len(members)
        attempts, successes = sum(r["attempts"] for r in members), sum(r["successes"] for r in members)
        stick = _stick(members, end_date, agg.households)
        base_6001 = [r for r in members if r["household_id"] in in_range]
        with_6001 = sum(r["household_id"] in (cohort_ids or ()) for r in base_6001)
        out.append({
            **common, "cohort": COHORT_HOUSEHOLD, "bucket": bucket, "households": n, "share": _rate(n, total),
            "censored_households": stick["censored_households"],
            "censored_share": _rate(stick["censored_households"], n),
            "sessions": sum(r["sessions"] for r in members), "attempts": attempts, "successes": successes,
            "success_rate": _rate(successes, attempts), "active_7plus_days": stick["active_7plus_days"],
            "active_7plus_rate": stick["active_7plus_rate"], "multi_week": stick["multi_week"],
            "multi_week_rate": stick["multi_week_rate"], "households_in_range": len(base_6001),
            "households_6001": "" if cohort_ids is None else with_6001,
            "rate_6001": "" if cohort_ids is None else _rate(with_6001, len(base_6001)),
        })
    g = agg.guests
    out.append({**common, "cohort": COHORT_GUEST, "bucket": "n/a (GUEST ids are per-install, no tenure)",
                "households": agg.guest_ids, "sessions": g.sessions, "attempts": g.attempts,
                "successes": g.successes, "success_rate": _rate(g.successes, g.attempts)})
    return out


def summarise_6001_tenure(rows: Sequence[dict], agg: Aggregation, config: AnalysisConfig, start: date, end: date,
                          tenant: str, earliest: date, cohort: Mapping[str, str] | None) -> list[dict]:
    """Tenure of households with a 6001 (by period of the first one) versus none, in ``start..end``."""
    if cohort is None:
        return []
    by_id = {r["household_id"]: r for r in rows}
    active_in: dict[str, set[str]] = defaultdict(set)
    for rec in agg.sessions:
        if rec.start_utc and start <= rec.start_ist <= end and rec.household_id in by_id:
            active_in[classify_period(rec.start_utc, None, config).period.value].add(rec.household_id)
    groups: dict[tuple[str, bool], list[dict]] = {}
    periods = sorted(set(active_in) | set(cohort.values()))
    for period in periods:
        groups[(period, False)] = [by_id[h] for h in active_in.get(period, ()) if h not in cohort]
        groups[(period, True)] = [by_id[h] for h, p in cohort.items() if p == period and h in by_id]
    note = limits_note(earliest, tenant)
    out = []
    for (period, flag), members in groups.items():
        tenures = [r["tenure_days"] for r in members]
        cens = sum(bool(r["censored"]) for r in members)
        out.append({"tenant": tenant, "base": f"households with a session (or first 6001) in {start}..{end}",
                    "period": period, "has_6001": flag, "households": len(members),
                    "median_tenure_days": statistics.median(tenures) if tenures else "",
                    "mean_tenure_days": round(statistics.fmean(tenures), 2) if tenures else "",
                    "censored_households": cens, "censored_share": _rate(cens, len(members)),
                    "earliest_retained_date": earliest.isoformat(), "limits_note": note})
    return out


def row_count_table(counts: Mapping[date, int], missing: Sequence[date], fraction: float, tenant: str,
                    earliest: date) -> list[dict]:
    """Per UTC file date row counts; days under ``fraction`` of the median are flagged (partial-day bias)."""
    median = statistics.median(counts.values()) if counts else 0
    note = limits_note(earliest, tenant)
    rows = [{"tenant": tenant, "file_date_utc": d.isoformat(), "session_rows": n,
             "small_day": n < fraction * median, "median_rows": median,
             "earliest_retained_date": earliest.isoformat(), "limits_note": note} for d, n in sorted(counts.items())]
    rows += [{"tenant": tenant, "file_date_utc": d.isoformat(), "session_rows": "missing", "small_day": "",
              "median_rows": median, "earliest_retained_date": earliest.isoformat(), "limits_note": note}
             for d in missing]
    return rows


def _failure_chart(household: list[dict], footer: str) -> bytes:
    rows = [b for b in household if b["attempts"]]
    if not rows:
        raise ChartError("no playback attempts in any tenure bucket")
    rates = [100 * (b["attempts"] - b["successes"]) / b["attempts"] for b in rows]
    newest, oldest = rates[0], rates[-1]
    return render_rate_bars(
        [RateRow(b["bucket"], r, f"{r:.1f}%   of {b['attempts']:,} attempts", "red" if r >= 0.8 * max(rates) else "dim_red")
         for b, r in zip(rows, rates)],
        title=f"Newest households fail {newest:.0f}% of playbacks; the oldest {oldest:.0f}%",
        subtitle="Share of playback attempts that did not succeed, by how long the household has been seen",
        footer=footer, vmax=100.0)


def _households_chart(household: list[dict], footer: str) -> bytes:
    rows = [b for b in household if b["households"]]
    total = sum(b["households"] for b in rows)
    if not total:
        raise ChartError("no active households")
    return render_composition(
        [Part(b["bucket"], b["households"], f"{b['households']:,} households", "blue" if i else "violet")
         for i, b in enumerate(rows)],
        title=f"{100 * rows[0]['households'] / total:.0f}% of active households were first seen within a week",
        subtitle=f"Active households by first-seen age bucket, {total:,} in total", footer=footer)


def render_charts(buckets: list[dict], out_dir: Path, tenant: str, label: str, earliest: date) -> list[Path]:
    """Failure rate by tenure bucket and a household composition bar; failures are logged, never raised."""
    household = [b for b in buckets if b["cohort"] == COHORT_HOUSEHOLD]
    foot = f"{tenant} {label.replace('_', ' to ')}; age = days since first seen, not subscription; unknown before {earliest}"
    written: list[Path] = []
    jobs = {
        f"{label}_user_tenure_success_by_bucket.png": lambda: _failure_chart(household, foot),
        f"{label}_user_tenure_households_by_bucket.png": lambda: _households_chart(household, foot),
    }
    for name, make in jobs.items():
        try:
            written.append(write_chart_png(make(), out_dir.parent, tenant, name))
        except (ChartError, OSError) as exc:
            LOGGER.error("tenure chart %s skipped: %s", name, exc)
    return written


def _read(path: Path, what: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise TenureError(f"{what} not found: {path}")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise TenureError(f"cannot read {path}: {exc}") from exc


def load_cohort_periods(path: Path) -> dict[str, str] | None:
    """Household id -> period of its first 6001 (guests skipped); None when the cohort file is absent."""
    if not path.is_file():
        return None
    rows = _read(path, "cohort file")
    if rows and any(c not in rows[0] for c in REQUIRED_COHORT_COLUMNS):
        raise TenureError(f"{path} lacks columns {REQUIRED_COHORT_COLUMNS}; is it the SU-10 cohort CSV?")
    result: dict[str, str] = {}
    for r in rows:
        if str(r["is_guest"]).strip().lower() in ("true", "1", "yes") or not r["household_id"]:
            continue
        result.setdefault(r["household_id"], r["period"] or "unknown")
    return result


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
    os.replace(tmp, path)


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date,
                        help="start of the range used for 6001 and output names")
    parser.add_argument("--end-date", type=date.fromisoformat, required=True, help="tenure is measured at this IST date")
    parser.add_argument("--history-start", type=date.fromisoformat, default=DEFAULT_HISTORY_START,
                        help="first local session-file date to read (first seen is measured from here)")
    parser.add_argument("--active-since", type=date.fromisoformat, default=DEFAULT_HISTORY_START,
                        help="active = at least one session on or after this date")
    parser.add_argument("--small-day-fraction", type=float, default=0.25,
                        help="days with fewer rows than this fraction of the median are flagged")
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--no-charts", action="store_true", help="skip the PNG charts")
    return parser


def load_history(sources: Sequence[Path], dates: Sequence[date]) -> tuple[list[dict[str, str]], dict[date, int], list[date]]:
    """Session rows plus per-file row counts and the dates found nowhere."""
    rows: list[dict[str, str]] = []
    counts: dict[date, int] = {}
    missing: list[date] = []
    for day in dates:
        loaded = load_daily(sources, SESSION_ARTIFACT, [day])
        if loaded.missing:
            missing.extend(loaded.missing)
            continue
        counts[day] = len(loaded.rows)
        rows.extend({**r, FILE_DATE_KEY: day.isoformat()} for r in loaded.rows)
    return rows, counts, missing


def notes_text(tenant: str, earliest: date, counts: Mapping[date, int], missing: Sequence[date],
               table: Sequence[dict], agg: Aggregation, cohort_found: bool) -> str:
    small = [r["file_date_utc"] for r in table if r["small_day"] is True]
    lines = [limits_note(earliest, tenant),
             f"earliest_retained_date={earliest.isoformat()} days_loaded={len(counts)} "
             f"rows_min={min(counts.values(), default=0)} rows_max={max(counts.values(), default=0)} "
             f"rows_median={statistics.median(counts.values()) if counts else 0}",
             f"small_days={len(small)} ({', '.join(small) or 'none'}): partial days push first seen later",
             "missing_dates=" + (",".join(d.isoformat() for d in missing) or "none"),
             f"sessions_dated_by_file_day_no_event_start={agg.file_dated_sessions} (kept; no period assigned) "
             f"sessions_undatable_dropped={agg.untimed_sessions} sessions_after_end_date={agg.outside_range_sessions} "
             f"sessions_without_household={agg.no_household_sessions}",
             "6001 columns: " + ("from the SU-10 cohort" if cohort_found else "empty (cohort file not found)")]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    named = lambda artifact: out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact)  # noqa: E731
    sources = default_sources(resolver, REPO_ROOT, args.tenant)
    raw, counts, missing = load_history(sources, date_range(args.history_start, args.end_date))
    if not counts:
        raise TenureError("no local session files found in the history range")
    earliest = min(counts)
    agg = aggregate(read_sessions(raw), args.active_since, args.end_date)
    cohort = load_cohort_periods(named(COHORT_ARTIFACT))
    rows = build_households(agg, active_since=args.active_since, end_date=args.end_date, earliest=earliest,
                            tenant=args.tenant, cohort=cohort)
    in_range = {r.household_id for r in agg.sessions if args.start_date <= r.start_ist <= args.end_date}
    buckets = summarise_buckets(rows, agg, args.end_date, args.tenant, earliest,
                                cohort_ids=None if cohort is None else set(cohort), in_range=in_range)
    sticky = summarise_stickiness(rows, agg, args.end_date, args.tenant, earliest)
    six = summarise_6001_tenure(rows, agg, config, args.start_date, args.end_date, args.tenant, earliest, cohort)
    table = row_count_table(counts, missing, args.small_day_fraction, args.tenant, earliest)
    for artifact, data, fields in ((HOUSEHOLDS_ARTIFACT, rows, HOUSEHOLD_FIELDS), (BUCKETS_ARTIFACT, buckets, BUCKET_FIELDS),
                                   (STICKINESS_ARTIFACT, sticky, STICKINESS_FIELDS), (SIX_ARTIFACT, six, SIX_FIELDS),
                                   (ROWCOUNT_ARTIFACT, table, ROWCOUNT_FIELDS)):
        write_table(named(artifact), data, fields)
    print(notes_text(args.tenant, earliest, counts, missing, table, agg, cohort is not None))
    print(f"households={len(rows)} guest_ids_separate={agg.guest_ids}; buckets: "
          + ", ".join(f"{b['bucket']}={b['households']}" for b in buckets if b["cohort"] == COHORT_HOUSEHOLD))
    if not args.no_charts:
        label = f"{args.start_date.isoformat()}_{args.end_date.isoformat()}"
        print(f"charts written: {len(render_charts(buckets, out_dir, args.tenant, label, earliest))}")
    LOGGER.info("Wrote tenure outputs for %s..%s", args.start_date, args.end_date)
    return 0


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-analyze-user-tenure")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    try:
        return run(args)
    except (TenureError, LocalDataError) as exc:
        LOGGER.error("analyze_user_tenure failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
