"""Session error impact: what share of unique sessions saw a PLAYER_ERROR, and how much of that is 6001?

Inputs (local files only, no Athena): per day the playback-outcome ``<date>_session.csv`` (the ``unified_sessions``
partition of that day) and the raw ``<date>_error_eventdata.csv`` (every ``PLAYER_ERROR`` of that day). A missing day in
either artifact fails loudly (``LocalDataError``); nothing is fetched.

Base and day basis: tenant ``--tenant`` (default ZA) and **UTC days** (the file's partition day), not the IST default of
the other analyses. Definitions:

* unique session = distinct ``sessionId`` in that day's session file;
* error-impacted session = a session whose ``sessionid`` (top level of ``eventdata``) is in a ``PLAYER_ERROR`` event of
  that day's error file, any error code, counted once however many events it has;
* 6001-impacted session = an error-impacted session with at least one 6001 event (``shaka_code`` 6001, falling back to
  ``errorcode`` 6001, i.e. E86001); a subset of the error-impacted sessions;
* other-error session = error-impacted without any 6001 event.

An error session need not be in that day's session file (error-only sessions, sessions straddling the UTC day), so every
day reports ``error_sessions`` and ``sessions_6001`` (all) next to ``error_sessions_in_session_file`` and
``sessions_6001_in_session_file`` (matched). The ``pct_*_of_unique`` columns use the matched numerators, so they cannot
exceed 100; ``pct_6001_of_error_sessions`` uses all error sessions. Error events without a ``sessionid`` are counted in
the log line, never in a session. The ``all`` row is the distinct union across the range (a session id seen on two days
counts once, and "in session file" means in any day's file). Rerunning overwrites the output.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.day_basis import DayBasis  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, load_daily  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileWriter  # noqa: E402
from src.lib.debug_events import flatten_row  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_session_error_impact")
SESSION_ARTIFACT = "session"
ERROR_ARTIFACT = "error_eventdata"
OUTPUT_ARTIFACT = "session_error_impact"
BASE = "unique sessions (distinct sessionId in the day's session file)"
DAY_BASIS = DayBasis.UTC.value
ALL_DAY = "all"
CODE_6001 = "6001"
PLAYER_ERROR = "PLAYER_ERROR"
FIELDNAMES = [
    "tenant", "base", "day_basis", "day", "unique_sessions", "error_sessions", "sessions_6001", "other_error_sessions",
    "error_sessions_in_session_file", "sessions_6001_in_session_file", "pct_error_of_unique", "pct_6001_of_unique",
    "pct_other_error_of_unique", "pct_6001_of_error_sessions",
]


@dataclass(frozen=True)
class DaySets:
    """The three session-id sets of one day (or of the whole range)."""
    sessions: frozenset[str]
    error: frozenset[str]
    code_6001: frozenset[str]


def session_ids(rows: Iterable[Mapping[str, str]]) -> set[str]:
    """Distinct non-blank ``sessionId`` values; rows without that column are not playback-outcome data."""
    ids: set[str] = set()
    for row in rows:
        if "sessionId" not in row:
            raise LocalDataError("session rows lack the sessionId column; not a session file")
        if sid := (row["sessionId"] or "").strip():
            ids.add(sid)
    return ids


def is_6001(flat: Mapping[str, object]) -> bool:
    """6001 as ``build_6001_cohort`` decides it (``shaka_code``), falling back to the top-level ``errorcode``."""
    code = flat.get("shaka_code")
    if code in (None, ""):
        code = flat.get("errorcode")
    return str(code).strip() == CODE_6001


def error_session_ids(rows: Iterable[Mapping[str, str]]) -> tuple[set[str], set[str], int]:
    """(all error session ids, those with a 6001 event, PLAYER_ERROR events without a sessionid)."""
    errors: set[str] = set()
    with_6001: set[str] = set()
    unattributed = 0
    for row in rows:
        if "eventdata" not in row:
            raise LocalDataError("error rows lack the eventdata column; not an error_eventdata file")
        if (row.get("eventid") or "").strip() != PLAYER_ERROR:
            continue
        flat = flatten_row(dict(row))
        sid = str(flat.get("session_id") or "").strip()
        if not sid:
            unattributed += 1
            continue
        errors.add(sid)
        if is_6001(flat):
            with_6001.add(sid)
    return errors, with_6001, unattributed


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.2f}" if whole else ""


def impact_row(day: str, sets: DaySets, tenant: str) -> dict[str, object]:
    """One output row; ``other`` is error minus 6001, matched counts are the intersection with the session file."""
    error_in = len(sets.error & sets.sessions)
    code_in = len(sets.code_6001 & sets.sessions)
    unique = len(sets.sessions)
    return {
        "tenant": tenant, "base": BASE, "day_basis": DAY_BASIS, "day": day, "unique_sessions": unique,
        "error_sessions": len(sets.error), "sessions_6001": len(sets.code_6001),
        "other_error_sessions": len(sets.error - sets.code_6001),
        "error_sessions_in_session_file": error_in, "sessions_6001_in_session_file": code_in,
        "pct_error_of_unique": _pct(error_in, unique), "pct_6001_of_unique": _pct(code_in, unique),
        "pct_other_error_of_unique": _pct(error_in - code_in, unique),
        "pct_6001_of_error_sessions": _pct(len(sets.code_6001), len(sets.error)),
    }


def build_table(per_day: Mapping[date, DaySets], tenant: str) -> list[dict[str, object]]:
    """One row per day in date order plus the distinct-union ``all`` row."""
    rows = [impact_row(day.isoformat(), sets, tenant) for day, sets in sorted(per_day.items())]
    union = DaySets(
        frozenset().union(*(s.sessions for s in per_day.values())),
        frozenset().union(*(s.error for s in per_day.values())),
        frozenset().union(*(s.code_6001 for s in per_day.values())),
    )
    rows.append(impact_row(ALL_DAY, union, tenant))
    return rows


def load_day_sets(sources: list[Path], days: list[date]) -> tuple[dict[date, DaySets], int]:
    """Per-day sets from the local files; any missing day in either artifact raises ``LocalDataError``."""
    per_day: dict[date, DaySets] = {}
    unattributed = 0
    for artifact in (SESSION_ARTIFACT, ERROR_ARTIFACT):
        missing = [d for d in days if load_daily(sources, artifact, [d]).missing]
        if missing:
            raise LocalDataError(f"no local {artifact} file for: {', '.join(d.isoformat() for d in missing)}")
    for day in days:
        sessions = session_ids(load_daily(sources, SESSION_ARTIFACT, [day]).rows)
        errors, with_6001, unattr = error_session_ids(load_daily(sources, ERROR_ARTIFACT, [day]).rows)
        unattributed += unattr
        per_day[day] = DaySets(frozenset(sessions), frozenset(errors), frozenset(with_6001))
    return per_day, unattributed


def write_table(path: Path, rows: list[dict[str, object]]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, FIELDNAMES)
    os.replace(tmp, path)


def build_parser(default_tenant: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 11, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 11, 5))
    parser.add_argument("--tenant", default=default_tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-analyze-session-error-impact")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    try:
        days = date_range(args.start_date, args.end_date)
        per_day, unattributed = load_day_sets(default_sources(resolver, REPO_ROOT, args.tenant), days)
    except LocalDataError as exc:
        LOGGER.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rows = build_table(per_day, args.tenant)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    out_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, OUTPUT_ARTIFACT)
    write_table(out_path, rows)
    print(f"tenant={args.tenant} day_basis={DAY_BASIS} base={BASE} -> {out_path}")
    print(f"error events without sessionid (not in any session)={unattributed}")
    LOGGER.info("Wrote %d rows to %s", len(rows), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
