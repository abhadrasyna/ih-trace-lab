"""Daily top-N households and devices hit by Shaka 6001.

Reads the SU-4 enriched CSV (one row per deduplicated 6001 debug event, UTC timestamps). Each event is assigned to a
day on ``--day-basis`` (IST by default, ``utc`` optional; stated in every output row and chart). Per day, households
and devices are ranked separately by 6001 events (ties: distinct sessions, then id) via ``src.lib.ranking``.
``GUEST.*`` ids are per-install, so they get their own ``_guest_`` tables and are never mixed into the real ranking;
events with no household/device id are counted per day in ``_unassigned.csv``, not dropped. Rates sit next to counts:
``top_share_pct`` is the top-N's share of that day's 6001 events (base: events, all ids incl. guests and unassigned).
``recovery_flag`` comes from the SU-11 members file ``<start>_<end>_6001_recovery_members.csv`` (default: the tenant
output folder; override with ``--recovery-csv``). Members are device+household pairs, so an id's flag aggregates its
scored members (status ``ok``): ``recovered`` if any recovered, else ``never_recovered``; empty when none was scored.
When the file is absent the column stays empty and a console note says so. Charts failing never block the CSVs. Local files only; rerunning overwrites the outputs.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.day_basis import DayBasis, DayBasisError, day_of, parse_utc  # noqa: E402
from scripts.lib.local_data import SLUG  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.ranking import rank_by_count  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.rank_daily_top_impacted")
INPUT_ARTIFACT = "shaka6001_enriched"
RECOVERY_ARTIFACT = "6001_recovery_members"
RECOVERY_COLUMNS = ("status", "recovered", "device_id", "household_id")
SCORED_STATUS = "ok"
GUEST_PREFIX = "GUEST."
DEFAULT_TOP = 10
UNKNOWN = "unknown"
REQUIRED_COLUMNS = ("datetime", "household_id", "device_id", "session_id", "device_model", "build_id",
                    "is_webview", "period", "app_version")
KINDS = {"households": "household_id", "devices": "device_id"}
FIELDS = ["tenant", "base", "day_basis", "day", "rank", "id", "events_6001", "distinct_sessions",
          "first_6001_ist", "last_6001_ist", "top_model", "top_build", "webview_share_pct", "periods_seen",
          "app_versions_seen", "recovery_flag", "top_n_events", "day_events", "top_share_pct"]
UNASSIGNED_FIELDS = ["tenant", "base", "day_basis", "day", "kind", "events_without_id", "day_events"]


class RankImpactedError(Exception):
    """The enriched input is missing, malformed or the arguments are inconsistent."""


def _mode(values: Iterable[str]) -> str:
    counts = Counter(v for v in values if v)
    if not counts:
        return UNKNOWN
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 2) if total else 0.0


def assign_days(rows: Iterable[dict[str, str]], basis: DayBasis, tz: ZoneInfo, start: date, end: date
                ) -> dict[date, list[dict]]:
    """Events grouped by day in [start, end]; each gets ``_ts`` (aware UTC). Bad timestamps raise."""
    if start > end:
        raise RankImpactedError(f"start {start} is after end {end}")
    by_day: dict[date, list[dict]] = defaultdict(list)
    for row in rows:
        try:
            ts = parse_utc(row.get("datetime", ""))
        except DayBasisError as exc:
            raise RankImpactedError(str(exc)) from exc
        day = day_of(ts, basis, tz)
        if start <= day <= end:
            by_day[day].append({**row, "_ts": ts})
    return dict(by_day)


def rank_day(events: list[dict], column: str, top: int, *, guests: bool, tz: ZoneInfo, recovery: dict[str, str]
             ) -> list[dict]:
    """Top-N rows for one id column of one day, real ids or ``GUEST.*`` ids only (per ``guests``)."""
    by_id: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        value = (ev.get(column) or "").strip()
        if value and value.startswith(GUEST_PREFIX) == guests:
            by_id[value].append(ev)
    sessions = {k: len({e.get("session_id") for e in v if e.get("session_id")}) for k, v in by_id.items()}
    flat = [e | {"_id": k} for k, v in by_id.items() for e in v]
    ranked = rank_by_count(flat, "_id", top=top, tie_breakers=(lambda k: -sessions[k], lambda k: k))
    out = []
    for item in ranked:
        evs = by_id[item["key"]]
        times = sorted(e["_ts"] for e in evs)
        wv = sum(1 for e in evs if (e.get("is_webview") or "").strip().lower() == "true")
        out.append({
            "rank": item["rank"], "id": item["key"], "events_6001": item["count"],
            "distinct_sessions": sessions[item["key"]],
            "first_6001_ist": times[0].astimezone(tz).isoformat(timespec="seconds"),
            "last_6001_ist": times[-1].astimezone(tz).isoformat(timespec="seconds"),
            "top_model": _mode((e.get("device_model") or "").strip() for e in evs),
            "top_build": _mode((e.get("build_id") or "").strip() for e in evs),
            "webview_share_pct": _pct(wv, len(evs)),
            "periods_seen": "|".join(sorted({(e.get("period") or "").strip() or UNKNOWN for e in evs})),
            "app_versions_seen": "|".join(sorted({(e.get("app_version") or "").strip() or UNKNOWN for e in evs})),
            "recovery_flag": recovery.get(item["key"], ""),
        })
    return out


def build_tables(by_day: dict[date, list[dict]], top: int, tz: ZoneInfo, tenant: str, basis: DayBasis,
                 recovery: dict[str, dict[str, str]] | None = None) -> tuple[dict[str, list[dict]], list[dict]]:
    """Tables keyed ``households|devices|guest_households|guest_devices`` plus the unassigned-event rows."""
    recovery = recovery or {}
    tables: dict[str, list[dict]] = {}
    unassigned: list[dict] = []
    for day in sorted(by_day):
        events = by_day[day]
        for kind, column in KINDS.items():
            for guests in (False, True):
                name = f"guest_{kind}" if guests else kind
                rows = rank_day(events, column, top, guests=guests, tz=tz, recovery=recovery.get(column, {}))
                top_n = sum(r["events_6001"] for r in rows)
                for r in rows:
                    tables.setdefault(name, []).append(
                        {"tenant": tenant, "base": "events", "day_basis": basis.value, "day": day.isoformat(),
                         **r, "top_n_events": top_n, "day_events": len(events),
                         "top_share_pct": _pct(top_n, len(events))})
                tables.setdefault(name, [])
            missing = sum(1 for e in events if not (e.get(column) or "").strip())
            unassigned.append({"tenant": tenant, "base": "events", "day_basis": basis.value, "day": day.isoformat(),
                               "kind": kind, "events_without_id": missing, "day_events": len(events)})
    for name in [*KINDS, *(f"guest_{k}" for k in KINDS)]:
        tables.setdefault(name, [])
    return tables, unassigned


def validate(rows: list[dict[str, str]]) -> None:
    if rows:
        missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
        if missing:
            raise RankImpactedError(f"enriched input lacks columns: {', '.join(missing)}")


def read_csv(path: Path, what: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise RankImpactedError(f"{what} not found: {path}")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError) as exc:
        raise RankImpactedError(f"cannot read {path}: {exc}") from exc


def read_recovery(path: Path | None) -> dict[str, dict[str, str]]:
    """``{id column: {id: flag}}`` from the SU-11 members file; empty when the file is absent.

    A device or household can have several members (device+household pairs): ``recovered`` if any scored member
    recovered, ``never_recovered`` if scored members exist and none recovered, no entry when none was scored.
    """
    if path is None or not path.is_file():
        return {}
    rows = read_csv(path, "recovery file")
    if rows and not set(RECOVERY_COLUMNS) <= set(rows[0]):
        raise RankImpactedError(f"recovery file needs columns {', '.join(RECOVERY_COLUMNS)}")
    flags: dict[str, dict[str, str]] = {"household_id": {}, "device_id": {}}
    for row in rows:
        if row["status"] != SCORED_STATUS:
            continue
        recovered = row["recovered"].strip().lower() == "true"
        for column, known in flags.items():
            ident = row[column].strip()
            if ident and (recovered or ident not in known):
                known[ident] = "recovered" if recovered else "never_recovered"
    return flags


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _draw_bar(rows: list[dict], title: str, subtitle: str) -> bytes:
    from src.lib.charts.errors import ChartError
    from src.lib.charts.rate_bars import RateRow, render_rate_bars

    ordered = sorted(rows, key=lambda r: -r["events_6001"])[:8]  # rate bars hold 8 rows
    if not ordered or not ordered[0]["events_6001"]:
        raise ChartError("top-impacted bar has no 6001 events")
    top = ordered[0]["events_6001"]
    return render_rate_bars(
        [RateRow(f"#{r['rank']} {str(r['id'])[:14]}", float(r["events_6001"]), f"{r['events_6001']:,} events", "blue")
         for r in ordered], title=title, subtitle="6001 events per id on the latest day", footer=subtitle,
        vmax=float(top) * 1.25, track=False)


def _draw_share_line(series: dict[str, list[tuple[str, float]]], title: str, subtitle: str) -> bytes:
    from src.lib.charts.errors import ChartError
    from src.lib.charts.trend import TrendSeries, render_trend

    days = [d for d, _ in next(iter(series.values()))]
    if any([d for d, _ in pts] != days for pts in series.values()):
        raise ChartError("top-share lines cover different days")
    names = ("blue", "violet", "pink", "slate", "sand")
    fmt = lambda v: f"{v:.0f}%"  # noqa: E731
    return render_trend(
        days, [TrendSeries(k, [v for _, v in pts], names[i % len(names)], end_text=f"{k}  {fmt(pts[-1][1])}")
               for i, (k, pts) in enumerate(series.items())],
        title=title, subtitle="Share of each day's 6001 events held by the top ids", footer=subtitle,
        lo=0.0, hi=100.0, ticks=[0, 25, 50, 75, 100], value_fmt=fmt)


def write_charts(tables: dict[str, list[dict]], out_dir: Path, tenant: str, basis: DayBasis, top: int,
                 stem: str) -> int:
    """Latest-day bars and the top-N share line; a chart failure is logged and counted, never raised."""
    from src.lib.charts.errors import ChartError
    from src.lib.charts.output import CHARTS_SUBDIR

    failures = 0
    jobs: list[tuple[str, bytes | None]] = []
    base = f"{tenant}, base: 6001 events, day basis {basis.value.upper()}"
    for kind in KINDS:
        rows = tables[kind]
        if not rows:
            continue
        latest = max(r["day"] for r in rows)
        jobs.append((f"{stem}_{kind}_latest_day.png",
                     lambda r=[x for x in rows if x["day"] == latest], k=kind, d=latest: _draw_bar(
                         r, f"Top {min(top, 8)} {k} by 6001 events, {d}", base)))
    series = {k: [(r["day"], r["top_share_pct"]) for r in dict((r["day"], r) for r in tables[k]).values()]
              for k in KINDS if tables[k]}
    if series:
        jobs.append((f"{stem}_top_share.png",
                     lambda: _draw_share_line(series, f"Top {top} share of daily 6001 events", base)))
    for filename, draw in jobs:
        try:
            png = draw()
            (out_dir / CHARTS_SUBDIR).mkdir(parents=True, exist_ok=True)
            (out_dir / CHARTS_SUBDIR / filename).write_bytes(png)
        except ChartError:
            failures += 1
            LOGGER.exception("chart %s failed; CSV outputs are unaffected", filename)
    return failures


def build_parser(default_start: date, default_tenant: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=default_start)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=default_tenant)
    parser.add_argument("--top", type=int, default=DEFAULT_TOP)
    parser.add_argument("--day-basis", choices=[b.value for b in DayBasis], default=DayBasis.IST.value)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--input", type=Path, default=None, help="enriched CSV (default: SU-4 output for the range)")
    parser.add_argument("--output-dir", type=Path, default=None, help="override the output folder (default: tenant output)")
    parser.add_argument("--recovery-csv", type=Path, default=None, help="SU-11 members file (default: <start>_<end>_6001_recovery_members.csv in the tenant output)")
    parser.add_argument("--no-charts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-rank-daily-top-impacted")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.default_start_date, config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = args.output_dir or resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    in_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    in_path = args.input or in_dir / resolver.format_range_filename(args.start_date, args.end_date, INPUT_ARTIFACT)
    basis = DayBasis(args.day_basis)
    recovery_path = args.recovery_csv or in_dir / resolver.format_range_filename(
        args.start_date, args.end_date, RECOVERY_ARTIFACT)
    try:
        if args.top < 1:
            raise RankImpactedError(f"--top must be >= 1, got {args.top}")
        rows = read_csv(in_path, "enriched events file (run build_enriched_events.py first)")
        validate(rows)
        by_day = assign_days(rows, basis, config.timezone, args.start_date, args.end_date)
        tables, unassigned = build_tables(by_day, args.top, config.timezone, args.tenant, basis,
                                          read_recovery(recovery_path))
    except RankImpactedError as exc:
        LOGGER.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not recovery_path.is_file():
        print(f"recovery_flag left empty: {recovery_path.name} not found (run analyze_6001_recovery.py)")
    for name, table in tables.items():
        artifact = f"6001_top{args.top}_{name}"
        write_rows(out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact), table, FIELDS)
    un_name = resolver.format_range_filename(args.start_date, args.end_date, f"6001_top{args.top}_unassigned")
    write_rows(out_dir / un_name, unassigned, UNASSIGNED_FIELDS)
    failures = 0
    if not args.no_charts:
        stem = f"{args.start_date}_{args.end_date}_6001_top{args.top}"
        failures = write_charts(tables, out_dir, args.tenant, basis, args.top, stem)
    print(f"tenant={args.tenant} base=events day_basis={basis.value} days={len(by_day)} "
          f"events={sum(len(v) for v in by_day.values())} chart_failures={failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
