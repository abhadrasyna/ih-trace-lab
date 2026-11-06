"""Shaka 6001 guest-login redirect analysis (SU-9), from the local SU-8 files only (no Athena, no network).

Reads ``<date>_guest_login_redirect.csv`` (base: navigation redirect rows, ``nav_event_time`` UTC) and
``<date>_guest_redirect_debug_events.csv`` (base: debug events of the redirected guests, ``clientid`` =
``<device_id>:<user_id>``) for ``--start-date``..``--end-date`` and writes under ``output/<tenant>/``:

* ``..._guest_redirect_daily.csv`` -- redirect rows and distinct guest ids per IST day, split by period;
* ``..._guest_redirect_periods.csv`` -- per period: rows, guest ids, debug-table match rate, steps ending the
  journey, guests with 6001 or a webview user agent in the events just before the redirect, and the measured
  rate of guests that also appear with a non-guest id;
* ``..._guest_redirect_steps.csv`` -- ``nav_step_total`` distribution, last-step and ``nav_end_event`` rates;
* ``..._guest_redirect_preceding.csv`` -- which debug events precede a guest's first redirect.

A guest's period comes from the ``appversion`` of its ``APP_DISCOVERY`` debug events (the last one at or before
its first redirect, else the earliest), not from the timestamp alone; with no discovery event the timestamp
decides outside the upgrade window and ``unknown`` inside it. ``GUEST.*`` ids are per-install, not real
households or devices: counts are distinct guest ids, never people. Whether a guest later has a non-guest id is a
measured match rate over the loaded debug events only, never assumed. Rerunning overwrites the outputs.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, load_daily  # noqa: E402
from scripts.lib.period import Period, classify_period  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.user_agent.parser import is_webview  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_guest_login_redirects")
REDIRECT_ARTIFACT = "guest_login_redirect"
DEBUG_ARTIFACT = "guest_redirect_debug_events"
REDIRECT_SCREEN = "guestLoginPrompt-redirect"
GUEST_PREFIX = "GUEST."
PRECEDING_EVENTS = 5
PERIODS = (Period.BEFORE.value, Period.AFTER.value, Period.UNKNOWN.value)
NOTE = "GUEST.* ids are per-install, not real households or devices"
BASE_ROWS = "redirect rows"
BASE_GUESTS = "distinct guest ids"
SIX_THOUSAND_ONE_RE = re.compile(r"(?<!\d)6001(?!\d)")
DAILY_FIELDS = ["tenant", "base", "ist_day", "redirect_rows", "guest_ids", "guests_before", "guests_after",
                "guests_unknown", "rows_per_guest", "note"]
PERIOD_FIELDS = [
    "tenant", "base", "period", "redirect_rows", "guest_ids", "rows_per_guest", "guests_with_debug_match",
    "debug_match_rate", "rows_ending_journey", "ending_journey_rate", "guests_6001_before_redirect",
    "guests_6001_rate", "guests_webview_ua", "guests_webview_rate", "guests_also_non_guest",
    "non_guest_match_rate", "note",
]
STEP_FIELDS = ["tenant", "base", "period", "nav_step_total", "rows", "row_share", "last_step_rows",
               "last_step_rate", "nav_end_event_rows", "nav_end_event_rate", "note"]
PRECEDING_FIELDS = ["tenant", "base", "period", "preceding_event", "guests", "guest_rate", "note"]


class GuestRedirectError(Exception):
    """Raised for missing or malformed inputs."""


def _share(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def parse_utc(value: str | None) -> datetime:
    """Parse a table timestamp (``2026-11-04 16:16:40.149`` or ``...T...Z``) as a UTC-aware datetime."""
    text = (value or "").strip().replace("Z", "")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise GuestRedirectError(f"unparseable timestamp {value!r}") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _eventdata(row: dict[str, str]) -> dict:
    try:
        data = json.loads(row.get("eventdata") or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def guest_clientid(row: dict[str, str]) -> str:
    return f"{row['device_id']}:{row['user_id']}"


def require_columns(rows: list[dict[str, str]], columns: tuple[str, ...], source: str) -> None:
    if rows and (missing := [c for c in columns if c not in rows[0]]):
        raise GuestRedirectError(f"{source} is missing column(s) {missing}")


def index_debug_events(rows: list[dict[str, str]]) -> dict[str, list[dict]]:
    """Debug events per clientid, sorted by UTC time, with parsed ``eventdata`` and time."""
    require_columns(rows, ("datetime", "clientid", "eventid", "eventdata"), "debug events")
    by_client: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_client[row["clientid"]].append({"ts": parse_utc(row["datetime"]), "eventid": row["eventid"],
                                           "raw": row.get("eventdata") or "", "data": _eventdata(row)})
    for events in by_client.values():
        events.sort(key=lambda e: e["ts"])
    return by_client


def guest_app_version(events: list[dict], first_redirect: datetime) -> str | None:
    """``appversion`` of the last APP_DISCOVERY at or before the first redirect, else the earliest one."""
    found = [(e["ts"], e["data"].get("appversion")) for e in events if e["eventid"] == "APP_DISCOVERY"
             and e["data"].get("appversion")]
    if not found:
        return None
    before = [v for ts, v in found if ts <= first_redirect]
    return before[-1] if before else found[0][1]


def guest_is_webview(events: list[dict]) -> bool:
    """True when a discovery event carries a user agent with the Android WebView ``; wv)`` token."""
    for event in events:
        if event["eventid"] != "APP_DISCOVERY":
            continue
        ua = (event["data"].get("deviceinfo") or {}).get("browserversion")
        if is_webview(ua if isinstance(ua, str) else None):
            return True
    return False


def preceding_events(events: list[dict], first_redirect: datetime, count: int = PRECEDING_EVENTS) -> list[dict]:
    """The ``count`` debug events strictly before the first redirect, excluding the redirect screen event itself."""
    earlier = [e for e in events if e["ts"] < first_redirect and e["data"].get("screenname") != REDIRECT_SCREEN]
    return earlier[-count:]


def event_label(event: dict) -> str:
    screen = event["data"].get("screenname")
    return f"{event['eventid']}:{screen}" if screen else event["eventid"]


def group_guests(redirects: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    require_columns(redirects, ("user_id", "device_id", "nav_event_time", "nav_step_num", "nav_step_total",
                                "nav_end_event"), "redirect rows")
    guests: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in redirects:
        guests[guest_clientid(row)].append(row)
    return guests


def classify_guest(clientid: str, rows: list[dict[str, str]], events: list[dict], config: AnalysisConfig) -> dict:
    first = min(parse_utc(r["nav_event_time"]) for r in rows)
    version = guest_app_version(events, first)
    result = classify_period(first, version, config)
    lead = preceding_events(events, first)
    return {
        "clientid": clientid, "first_redirect": first, "app_version": version, "period": result.period.value,
        "has_debug": bool(events), "webview": guest_is_webview(events), "preceding": lead,
        "six_thousand_one": any(SIX_THOUSAND_ONE_RE.search(e["raw"]) for e in lead),
    }


def non_guest_device_match(guest_devices: set[str], by_client: dict[str, list[dict]]) -> tuple[set[str], bool]:
    """Devices that also appear with a non-guest user id in the loaded debug events, and whether any non-guest id was loaded."""
    non_guest = {c.split(":", 1)[0] for c in by_client if ":" in c and not c.split(":", 1)[1].startswith(GUEST_PREFIX)}
    return guest_devices & non_guest, bool(non_guest)


def daily_table(redirects: list[dict[str, str]], guests: dict[str, dict], config: AnalysisConfig) -> list[dict]:
    rows_by_day: Counter[date] = Counter()
    guests_by_day: dict[date, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in redirects:
        clientid = guest_clientid(row)
        day = parse_utc(row["nav_event_time"]).astimezone(config.timezone).date()
        rows_by_day[day] += 1
        guests_by_day[day][guests[clientid]["period"]].add(clientid)
    table = []
    for day in sorted(rows_by_day):
        all_ids = set().union(*guests_by_day[day].values())
        table.append({
            "tenant": config.tenant, "base": f"{BASE_ROWS} / {BASE_GUESTS} per IST day", "ist_day": day.isoformat(),
            "redirect_rows": rows_by_day[day], "guest_ids": len(all_ids),
            **{f"guests_{p}": len(guests_by_day[day][p]) for p in PERIODS},
            "rows_per_guest": round(rows_by_day[day] / len(all_ids), 3), "note": NOTE,
        })
    return table


def _in_period(period: str, value: str) -> bool:
    return period == "all" or value == period


def period_table(guests: dict[str, dict], rows_by_guest: dict[str, list[dict[str, str]]], matched: set[str],
                 non_guest_loaded: bool, tenant: str) -> list[dict]:
    table = []
    for period in (*PERIODS, "all"):
        ids = [c for c, g in guests.items() if _in_period(period, g["period"])]
        rows = [r for c in ids for r in rows_by_guest[c]]
        n = len(ids)
        debug = sum(guests[c]["has_debug"] for c in ids)
        ending = sum(r["nav_end_event"].strip().lower() == "true" for r in rows)
        six = sum(guests[c]["six_thousand_one"] for c in ids)
        wv = sum(guests[c]["webview"] for c in ids)
        also = sum(c.split(":", 1)[0] in matched for c in ids)
        table.append({
            "tenant": tenant, "base": f"{BASE_ROWS} / {BASE_GUESTS}", "period": period,
            "redirect_rows": len(rows), "guest_ids": n, "rows_per_guest": round(len(rows) / n, 3) if n else 0.0,
            "guests_with_debug_match": debug, "debug_match_rate": _share(debug, n),
            "rows_ending_journey": ending, "ending_journey_rate": _share(ending, len(rows)),
            "guests_6001_before_redirect": six, "guests_6001_rate": _share(six, n),
            "guests_webview_ua": wv, "guests_webview_rate": _share(wv, n),
            "guests_also_non_guest": also if non_guest_loaded else "not_measurable",
            "non_guest_match_rate": _share(also, n) if non_guest_loaded else "not_measurable",
            "note": NOTE,
        })
    return table


def step_table(guests: dict[str, dict], rows_by_guest: dict[str, list[dict[str, str]]], tenant: str) -> list[dict]:
    table = []
    for period in (*PERIODS, "all"):
        rows = [r for c, g in guests.items() if _in_period(period, g["period"]) for r in rows_by_guest[c]]
        totals = Counter(r["nav_step_total"] for r in rows)
        for total in sorted(totals, key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else 0, v)):
            subset = [r for r in rows if r["nav_step_total"] == total]
            last = sum(r["nav_step_num"] == r["nav_step_total"] for r in subset)
            ended = sum(r["nav_end_event"].strip().lower() == "true" for r in subset)
            table.append({
                "tenant": tenant, "base": BASE_ROWS, "period": period, "nav_step_total": total, "rows": len(subset),
                "row_share": _share(len(subset), len(rows)), "last_step_rows": last,
                "last_step_rate": _share(last, len(subset)), "nav_end_event_rows": ended,
                "nav_end_event_rate": _share(ended, len(subset)), "note": NOTE,
            })
    return table


def preceding_table(guests: dict[str, dict], tenant: str) -> list[dict]:
    table = []
    for period in (*PERIODS, "all"):
        with_context = [g for g in guests.values() if _in_period(period, g["period"]) and g["preceding"]]
        counts = Counter(label for g in with_context for label in {event_label(e) for e in g["preceding"]})
        base = f"{BASE_GUESTS} with debug events before the redirect (last {PRECEDING_EVENTS})"
        for label, n in counts.most_common():
            table.append({"tenant": tenant, "base": base, "period": period, "preceding_event": label, "guests": n,
                          "guest_rate": _share(n, len(with_context)), "note": NOTE})
    return table


def analyse(redirects: list[dict[str, str]], debug_rows: list[dict[str, str]], config: AnalysisConfig) -> dict:
    """All tables from already-loaded rows; pure logic, no I/O."""
    rows_by_guest = group_guests(redirects)
    by_client = index_debug_events(debug_rows)
    guests = {c: classify_guest(c, rows, by_client.get(c, []), config) for c, rows in rows_by_guest.items()}
    matched, non_guest_loaded = non_guest_device_match({c.split(":", 1)[0] for c in guests}, by_client)
    return {
        "daily": daily_table(redirects, guests, config),
        "periods": period_table(guests, rows_by_guest, matched, non_guest_loaded, config.tenant),
        "steps": step_table(guests, rows_by_guest, config.tenant),
        "preceding": preceding_table(guests, config.tenant),
    }


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
    os.replace(tmp, path)


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="directory with the SU-8 daily files (default: the tenant's investigation data dir)")
    parser.add_argument("--output-dir", type=Path, default=None, help="output directory (default: the tenant's output dir)")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-analyze-guest-login-redirects")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    try:
        resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
        data_dir = args.data_dir or resolver.resolve_investigation_data_dir(SLUG, "athena", tenant=args.tenant)
        out_dir = args.output_dir or resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
        dates = date_range(args.start_date, args.end_date)
        redirects = load_daily([data_dir], REDIRECT_ARTIFACT, dates)
        debug = load_daily([data_dir], DEBUG_ARTIFACT, dates)
        if not redirects.found:
            raise GuestRedirectError(f"no {REDIRECT_ARTIFACT} files for {args.start_date}..{args.end_date} in {data_dir}")
        tables = analyse(redirects.rows, debug.rows, config if args.tenant == config.tenant else _retenant(config, args.tenant))
    except (GuestRedirectError, LocalDataError) as exc:
        LOGGER.error("Guest-login redirect analysis failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    stem = f"{args.start_date.isoformat()}_{args.end_date.isoformat()}"
    for name, fields in (("daily", DAILY_FIELDS), ("periods", PERIOD_FIELDS), ("steps", STEP_FIELDS),
                         ("preceding", PRECEDING_FIELDS)):
        write_table(out_dir / f"{stem}_guest_redirect_{name}.csv", tables[name], fields)
    summary = next(r for r in tables["periods"] if r["period"] == "all")
    print(f"tenant={args.tenant} base={BASE_ROWS} redirect_rows={summary['redirect_rows']} guest_ids={summary['guest_ids']} "
          f"debug_match={summary['guests_with_debug_match']} ({summary['debug_match_rate']:.1%} of guest ids) "
          f"rows_ending_journey={summary['rows_ending_journey']} ({summary['ending_journey_rate']:.1%} of rows) "
          f"non_guest_match={summary['guests_also_non_guest']} ({summary['non_guest_match_rate']})")
    print(f"missing_redirect_dates={','.join(d.isoformat() for d in redirects.missing) or 'none'} "
          f"missing_debug_dates={','.join(d.isoformat() for d in debug.missing) or 'none'}; {NOTE}")
    LOGGER.info("Wrote guest-login redirect tables to %s", out_dir)
    return 0


def _retenant(config: AnalysisConfig, tenant: str) -> AnalysisConfig:
    from dataclasses import replace

    return replace(config, tenant=tenant)


if __name__ == "__main__":
    sys.exit(main())
