"""Did 6001 users recover? Per-member recovery and recovery rates by period, webview and device model.

Inputs (same ``--start-date/--end-date`` range, all local, no Athena): the SU-10 cohort CSV
(``<start>_<end>_6001_cohort.csv``), the SU-4 enriched events (only to learn which ``session_id`` each member's 6001s
were in) and the per-date ``<date>_session.csv`` playback outcomes. A session succeeds only when
``playback_outcome == "DESTROY"`` (``src.lib.playback.is_success``).

Per member (device+household), anchored on its first 6001 (``T``): successful sessions before ``T``, after ``T``
(cross-session), and after ``T`` on the same IST day; the time from ``T`` to the next success; and a never-recovered
flag. Two recovery paths are kept apart: *same-session* (a session that carried a 6001 and still ended DESTROY, the
success is dated by its ``event_end``) and *cross-session* (a different session starting at or after ``T``). A member
counts as recovered if either happens; the two overlap, so their counts do not sum to ``recovered``. Sessions with no
``event_start`` cannot be placed in time and are counted per member (``sessions_untimed``), not used for before/after.

Rates: ``recovered / members`` where the base is *members with at least one session row and a readable first-6001
time*; members without session rows or time are listed as their own counts, never as failures. Every table row states
its base (households/devices) and tenant. ``GUEST.*`` ids are per-install, not real households or devices, so guests
form their own ``cohort`` value and are never mixed into the household rows. Recovery is censored by the data range:
a member whose first 6001 is near the end of the range had little time to recover. Timestamps are UTC; the same-day
test converts to IST. Rerunning overwrites the outputs. A chart failure is logged and never blocks the CSVs.
"""

from __future__ import annotations

import argparse
import logging
import os
import statistics
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.build_6001_cohort import IST, SESSION_ARTIFACT, _parse_utc  # noqa: E402
from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, load_daily  # noqa: E402
from src.lib.charts.errors import ChartError  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402
from src.lib.charts.stacked_bar import render_stacked_bar  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.playback import is_success  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_6001_recovery")
COHORT_ARTIFACT = "6001_cohort"
ENRICHED_ARTIFACT = "shaka6001_enriched"
MEMBERS_ARTIFACT = "6001_recovery_members"
SUMMARY_ARTIFACT = "6001_recovery_summary"
BASE = "households/devices with session rows and a first-6001 time"
COHORT_HOUSEHOLD = "household"
COHORT_GUEST = "guest"
REQUIRED_COHORT_COLUMNS = ("device_id", "household_id", "is_guest", "first_6001_utc", "period", "is_webview", "device_model")
MEMBER_FIELDS = [
    "tenant", "cohort", "clientid", "device_id", "household_id", "period", "is_webview", "device_model",
    "first_6001_ist", "status", "session_rows", "sessions_untimed", "success_before", "success_after",
    "success_same_day", "success_same_session", "recovered", "recovery_path", "minutes_to_next_success",
    "never_recovered",
]
SUMMARY_FIELDS = [
    "tenant", "base", "cohort", "dimension", "group", "members", "recovered", "recovery_rate",
    "same_session", "same_session_rate", "cross_session", "cross_session_rate", "cross_same_day",
    "cross_later_day", "never_recovered", "never_recovered_rate", "median_minutes_to_next_success",
    "members_without_session_rows", "members_without_first_6001_time", "low_n",
]
STATUS_OK = "ok"
STATUS_NO_SESSIONS = "no_session_rows"
STATUS_NO_TIME = "no_first_6001_time"


class RecoveryError(Exception):
    """Raised for missing or malformed inputs."""


@dataclass(frozen=True)
class Session:
    session_id: str
    success: bool
    start: datetime | None
    end: datetime | None


def _read(path: Path, what: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise RecoveryError(f"{what} not found: {path}")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError(f"cannot read {path}: {exc}") from exc


def _is_true(value: object) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def load_cohort(path: Path) -> list[dict[str, str]]:
    rows = _read(path, "cohort file")
    if rows:
        missing = [c for c in REQUIRED_COHORT_COLUMNS if c not in rows[0]]
        if missing:
            raise RecoveryError(f"{path} lacks columns {missing}; is it the SU-10 cohort CSV?")
    return rows


def sessions_by_member(session_rows: Iterable[Mapping[str, str]]) -> dict[tuple[str, str], list[Session]]:
    """Group playback-outcome rows by (device, household); a session id seen twice is kept once (first row wins)."""
    grouped: dict[tuple[str, str], dict[str, Session]] = defaultdict(dict)
    for row in session_rows:
        if "deviceId" not in row or "householdId" not in row:
            raise RecoveryError("session rows lack deviceId/householdId; not playback-outcome data")
        key = ((row.get("deviceId") or "").strip(), (row.get("householdId") or "").strip())
        sid = (row.get("sessionId") or "").strip()
        session = Session(sid, is_success(row.get("playback_outcome")),
                          _parse_utc(row.get("event_start")), _parse_utc(row.get("event_end")))
        grouped[key].setdefault(sid or f"~row{len(grouped[key])}", session)
    return {key: list(by_id.values()) for key, by_id in grouped.items()}


def sessions_with_6001(enriched_rows: Iterable[Mapping[str, str]]) -> dict[tuple[str, str], set[str]]:
    """Session ids that carried a 6001, per (device, household)."""
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in enriched_rows:
        if (row.get("shaka_code") or "6001").strip() != "6001":
            continue
        sid = (row.get("session_id") or "").strip()
        if sid:
            key = ((row.get("device_id") or "").strip(), (row.get("household_id") or "").strip())
            result[key].add(sid)
    return result


def analyse_member(member: Mapping[str, str], sessions: list[Session], six_sessions: set[str], tenant: str) -> dict:
    """One output row for a cohort member; see the module docstring for the definitions."""
    device, household = member["device_id"], member["household_id"]
    first = _parse_utc(member.get("first_6001_utc"))
    row = {
        "tenant": tenant, "clientid": f"{device}:{household}", "device_id": device, "household_id": household,
        "cohort": COHORT_GUEST if _is_true(member["is_guest"]) else COHORT_HOUSEHOLD,
        "period": member.get("period") or "unknown", "is_webview": member.get("is_webview", ""),
        "device_model": member.get("device_model", ""), "first_6001_ist": member.get("first_6001_ist", ""),
        "session_rows": len(sessions), "sessions_untimed": 0, "success_before": 0, "success_after": 0,
        "success_same_day": 0, "success_same_session": 0, "recovered": False, "recovery_path": "",
        "minutes_to_next_success": "", "never_recovered": False,
    }
    if not sessions:
        return {**row, "status": STATUS_NO_SESSIONS}
    if first is None:
        return {**row, "status": STATUS_NO_TIME}
    first_day = first.astimezone(IST).date()
    candidates: list[datetime] = []
    same_session = cross_session = False
    for s in sessions:
        if s.start is None:
            row["sessions_untimed"] += 1
        if not s.success:
            continue
        if s.session_id in six_sessions:
            row["success_same_session"] += 1
            same_session = True
            if (s.end or s.start) is not None:
                candidates.append(max(s.end or s.start, first))
            continue
        if s.start is None:
            continue
        if s.start < first:
            row["success_before"] += 1
            continue
        row["success_after"] += 1
        cross_session = True
        row["success_same_day"] += s.start.astimezone(IST).date() == first_day
        candidates.append(s.start)
    recovered = same_session or cross_session
    row.update(status=STATUS_OK, recovered=recovered, never_recovered=not recovered,
               recovery_path=_path_label(same_session, cross_session))
    if candidates:
        row["minutes_to_next_success"] = round((min(candidates) - first).total_seconds() / 60, 2)
    return row


def _path_label(same_session: bool, cross_session: bool) -> str:
    return {(True, True): "both", (True, False): "same_session", (False, True): "cross_session"}.get(
        (same_session, cross_session), "never")


def analyse_members(cohort: list[dict[str, str]], sessions: Mapping[tuple[str, str], list[Session]],
                    six_sessions: Mapping[tuple[str, str], set[str]], tenant: str) -> list[dict]:
    return [
        analyse_member(m, sessions.get((m["device_id"], m["household_id"]), []),
                       six_sessions.get((m["device_id"], m["household_id"]), set()), tenant)
        for m in cohort
    ]


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _webview_label(value: object) -> str:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return "webview"
    return "non-webview" if text in ("false", "0", "no") else "unknown"


DIMENSIONS = {
    "period": lambda r: r["period"] or "unknown",
    "webview": lambda r: _webview_label(r["is_webview"]),
    "period_webview": lambda r: f"{r['period'] or 'unknown'}|{_webview_label(r['is_webview'])}",
    "device_model": lambda r: r["device_model"] or "unknown",
}


def summarise(members: list[dict], tenant: str, min_members: int) -> list[dict]:
    """Recovery rates per cohort and dimension; households and guests never share a row."""
    out: list[dict] = []
    for cohort in (COHORT_HOUSEHOLD, COHORT_GUEST):
        cohort_rows = [m for m in members if m["cohort"] == cohort]
        no_sessions = sum(m["status"] == STATUS_NO_SESSIONS for m in cohort_rows)
        no_time = sum(m["status"] == STATUS_NO_TIME for m in cohort_rows)
        scored = [m for m in cohort_rows if m["status"] == STATUS_OK]
        for dimension, key in DIMENSIONS.items():
            groups: dict[str, list[dict]] = defaultdict(list)
            for m in scored:
                groups[key(m)].append(m)
            for group in sorted(groups):
                out.append(_summary_row(tenant, cohort, dimension, group, groups[group], min_members,
                                        no_sessions, no_time))
        if not scored:
            out.append(_summary_row(tenant, cohort, "all", "all", [], min_members, no_sessions, no_time))
    return out


def _summary_row(tenant: str, cohort: str, dimension: str, group: str, rows: list[dict], min_members: int,
                 no_sessions: int, no_time: int) -> dict:
    n = len(rows)
    paths = [r["recovery_path"] for r in rows]
    same = sum(p in ("same_session", "both") for p in paths)
    cross = sum(p in ("cross_session", "both") for p in paths)
    recovered = sum(bool(r["recovered"]) for r in rows)
    never = n - recovered
    minutes = [r["minutes_to_next_success"] for r in rows if r["minutes_to_next_success"] != ""]
    return {
        "tenant": tenant, "base": BASE, "cohort": cohort, "dimension": dimension, "group": group, "members": n,
        "recovered": recovered, "recovery_rate": _rate(recovered, n),
        "same_session": same, "same_session_rate": _rate(same, n),
        "cross_session": cross, "cross_session_rate": _rate(cross, n),
        "cross_same_day": sum(1 for r in rows if r["success_same_day"] > 0),
        "cross_later_day": sum(1 for r in rows if r["success_after"] > r["success_same_day"]),
        "never_recovered": never, "never_recovered_rate": _rate(never, n),
        "median_minutes_to_next_success": round(statistics.median(minutes), 2) if minutes else "",
        "members_without_session_rows": no_sessions, "members_without_first_6001_time": no_time,
        "low_n": n < min_members,
    }


def render_charts(summary: list[dict], out_dir: Path, tenant: str, range_label: str) -> list[Path]:
    """100% stacked bars (recovered vs not) per cohort for period and webview; a failure is logged, never raised."""
    written: list[Path] = []
    for cohort in (COHORT_HOUSEHOLD, COHORT_GUEST):
        for dimension in ("period", "webview"):
            rows = [r for r in summary if r["cohort"] == cohort and r["dimension"] == dimension and r["members"]]
            if not rows:
                continue
            labels = [f"{r['group']} (n={r['members']})" for r in rows]
            series = {"recovered": [r["recovered"] for r in rows], "not recovered": [r["never_recovered"] for r in rows]}
            try:
                png = render_stacked_bar(
                    labels, series, normalize=True, colours={"recovered": "green", "not recovered": "red"},
                    title=f"6001 recovery by {dimension} ({cohort} cohort)",
                    subtitle=f"{tenant} {range_label} · base: {BASE}"
                             + (" · GUEST ids are per-install, not households" if cohort == COHORT_GUEST else ""))
                written.append(write_chart_png(png, out_dir.parent, tenant, f"{range_label}_6001_recovery_{cohort}_by_{dimension}.png"))
            except (ChartError, OSError) as exc:
                LOGGER.error("recovery chart %s/%s skipped: %s", cohort, dimension, exc)
    return written


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
    os.replace(tmp, path)


def coverage_line(members: list[dict], missing_dates: list[date], tenant: str) -> str:
    by_status = {s: sum(m["status"] == s for m in members) for s in (STATUS_OK, STATUS_NO_SESSIONS, STATUS_NO_TIME)}
    guests = sum(m["cohort"] == COHORT_GUEST for m in members)
    return (f"tenant={tenant} base=households/devices members={len(members)} (guests={guests}, kept separate) "
            f"scored={by_status[STATUS_OK]} no_session_rows={by_status[STATUS_NO_SESSIONS]} "
            f"no_first_6001_time={by_status[STATUS_NO_TIME]} (counted, not failures) "
            f"session_dates_missing=" + (",".join(d.isoformat() for d in missing_dates) or "none"))


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--min-members", type=int, default=20,
                        help="groups with fewer scored members are flagged low_n, not hidden")
    parser.add_argument("--no-charts", action="store_true", help="skip the PNG charts")
    return parser


def run(args: argparse.Namespace) -> int:
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    named = lambda artifact: out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact)  # noqa: E731
    cohort = load_cohort(named(COHORT_ARTIFACT))
    six_sessions = sessions_with_6001(_read(named(ENRICHED_ARTIFACT), "enriched events"))
    dates = date_range(args.start_date, args.end_date)
    loaded = load_daily(default_sources(resolver, REPO_ROOT, args.tenant), SESSION_ARTIFACT, dates)
    members = analyse_members(cohort, sessions_by_member(loaded.rows), six_sessions, args.tenant)
    summary = summarise(members, args.tenant, args.min_members)
    write_table(named(MEMBERS_ARTIFACT), members, MEMBER_FIELDS)
    write_table(named(SUMMARY_ARTIFACT), summary, SUMMARY_FIELDS)
    print(f"wrote {len(members)} members -> {named(MEMBERS_ARTIFACT)}; {len(summary)} summary rows -> {named(SUMMARY_ARTIFACT)}")
    print(coverage_line(members, loaded.missing, args.tenant))
    if not args.no_charts:
        label = f"{args.start_date.isoformat()}_{args.end_date.isoformat()}"
        print(f"charts written: {len(render_charts(summary, out_dir, args.tenant, label))}")
    LOGGER.info("Wrote 6001 recovery outputs for %s..%s", args.start_date, args.end_date)
    return 0


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-analyze-6001-recovery")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    try:
        return run(args)
    except (RecoveryError, LocalDataError) as exc:
        LOGGER.error("analyze_6001_recovery failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
