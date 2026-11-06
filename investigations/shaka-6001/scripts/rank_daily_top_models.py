"""Daily top-N device models hit by Shaka 6001.

Reads the SU-4 enriched CSV (one row per deduplicated 6001 debug event, UTC timestamps). Each event is assigned to a
day on ``--day-basis`` (IST by default; shared with SU-12 via ``scripts.lib.day_basis``) and models are ranked per day
by 6001 events via ``src.lib.ranking`` (ties: distinct devices, then model name). The model is the key; the build is
a separate ``top_build`` column, so one model across builds is one row. Unparsed shapes keep their own labelled rows
(reduced-UA ``K``, desktop, iOS, and ``(no user agent)`` when the model is empty). ``GUEST.*`` events stay in the count
because the model is on the event; ``guest_events`` shows how many they are.

Rates sit next to counts. Base: 6001 events (the enriched file holds no non-error traffic, so there is no per-model
total of all playback). ``day_events`` is every 6001 event that day and ``share_of_day_pct`` the model's share of it;
``events_per_session`` is events over the model's distinct 6001 sessions. Models below ``--min-events`` are flagged
``low_traffic=True``, not hidden. A chart failure never blocks the CSV. Local files only; reruns overwrite outputs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.day_basis import DayBasis  # noqa: E402
from scripts.lib.local_data import SLUG  # noqa: E402
from scripts.rank_daily_top_impacted import (  # noqa: E402
    GUEST_PREFIX, INPUT_ARTIFACT, UNKNOWN, RankImpactedError, _mode, _pct, assign_days, read_csv, write_rows,
)
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.ranking import rank_by_count  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.rank_daily_top_models")
DEFAULT_TOP = 10
DEFAULT_MIN_EVENTS = 20
NO_UA_LABEL = "(no user agent)"
OTHER_LABEL = "Other models"
REQUIRED_COLUMNS = ("datetime", "household_id", "device_id", "session_id", "device_model", "build_id", "os_name",
                    "os_version", "chrome_version", "is_webview", "ua_shape", "period", "app_version")
FIELDS = ["tenant", "base", "day_basis", "day", "rank", "model", "ua_shape", "events_6001", "distinct_devices",
          "distinct_households", "distinct_sessions", "guest_events", "webview_share_pct", "top_android_version",
          "top_chrome_version", "top_build", "periods_seen", "app_versions_seen", "day_events", "share_of_day_pct",
          "events_per_session", "low_traffic", "top_n_events", "top_share_pct"]


class RankModelsError(Exception):
    """The enriched input is malformed or the arguments are inconsistent."""


def model_label(event: dict) -> str:
    return (event.get("device_model") or "").strip() or NO_UA_LABEL


def _distinct(events: list[dict], column: str) -> int:
    return len({(e.get(column) or "").strip() for e in events} - {""})


def rank_models_for_day(events: list[dict], top: int, min_events: int) -> list[dict]:
    """Top-N model rows for one day (every event counts, guest or not)."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_model[model_label(ev)].append(ev)
    devices = {m: _distinct(v, "device_id") for m, v in by_model.items()}
    flat = [e | {"_model": m} for m, v in by_model.items() for e in v]
    ranked = rank_by_count(flat, "_model", top=top, tie_breakers=(lambda m: -devices[m], lambda m: m))
    out = []
    for item in ranked:
        evs, name = by_model[item["key"]], item["key"]
        sessions = _distinct(evs, "session_id")
        wv = sum(1 for e in evs if (e.get("is_webview") or "").strip().lower() == "true")
        android = [(e.get("os_version") or "").strip() for e in evs if (e.get("os_name") or "").strip() == "Android"]
        out.append({
            "rank": item["rank"], "model": name,
            "ua_shape": _mode((e.get("ua_shape") or "").strip() for e in evs),
            "events_6001": item["count"], "distinct_devices": devices[name],
            "distinct_households": _distinct(evs, "household_id"), "distinct_sessions": sessions,
            "guest_events": sum(1 for e in evs if (e.get("household_id") or "").startswith(GUEST_PREFIX)
                                or (e.get("device_id") or "").startswith(GUEST_PREFIX)),
            "webview_share_pct": _pct(wv, len(evs)), "top_android_version": _mode(android),
            "top_chrome_version": _mode((e.get("chrome_version") or "").strip() for e in evs),
            "top_build": _mode((e.get("build_id") or "").strip() for e in evs),
            "periods_seen": "|".join(sorted({(e.get("period") or "").strip() or UNKNOWN for e in evs})),
            "app_versions_seen": "|".join(sorted({(e.get("app_version") or "").strip() or UNKNOWN for e in evs})),
            "events_per_session": round(item["count"] / sessions, 2) if sessions else 0.0,
            "low_traffic": item["count"] < min_events,
        })
    return out


def build_table(by_day: dict[date, list[dict]], top: int, min_events: int, tenant: str, basis: DayBasis
                ) -> list[dict]:
    table: list[dict] = []
    for day in sorted(by_day):
        events = by_day[day]
        rows = rank_models_for_day(events, top, min_events)
        top_n = sum(r["events_6001"] for r in rows)
        for r in rows:
            table.append({"tenant": tenant, "base": "events", "day_basis": basis.value, "day": day.isoformat(),
                          **r, "day_events": len(events), "share_of_day_pct": _pct(r["events_6001"], len(events)),
                          "top_n_events": top_n, "top_share_pct": _pct(top_n, len(events))})
    return table


def validate(rows: list[dict[str, str]]) -> None:
    if rows:
        missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
        if missing:
            raise RankModelsError(f"enriched input lacks columns: {', '.join(missing)}")


def day_split(table: list[dict]) -> tuple[list[str], list[int], list[int]]:
    """Per day: top-N events and the remaining ``other`` events, for the stacked bar."""
    days: dict[str, dict] = {}
    for r in table:
        days.setdefault(r["day"], {"top": r["top_n_events"], "all": r["day_events"]})
    labels = sorted(days)
    return labels, [days[d]["top"] for d in labels], [days[d]["all"] - days[d]["top"] for d in labels]


def write_charts(table: list[dict], out_dir: Path, tenant: str, basis: DayBasis, top: int, stem: str) -> int:
    """Latest-day share bars and per-day top-model share columns; a chart failure is logged and counted, never raised."""
    from src.lib.charts.columns import Column, render_columns
    from src.lib.charts.errors import ChartError
    from src.lib.charts.output import CHARTS_SUBDIR
    from src.lib.charts.rate_bars import RateRow, render_rate_bars

    if not table:
        return 0
    footer = f"{tenant}, base: 6001 events, day basis {basis.value.upper()}"
    latest = max(r["day"] for r in table)
    rows = sorted((r for r in table if r["day"] == latest), key=lambda r: r["events_6001"], reverse=True)[:8]
    day_total = rows[0]["day_events"] if rows else 0
    labels, tops, others = day_split(table)
    shares = [100 * t / (t + o) if t + o else 0.0 for t, o in zip(tops, others)]
    jobs = [
        (f"{stem}_models_latest_day.png", lambda: render_rate_bars(
            [RateRow(str(r["model"]), 100 * r["events_6001"] / day_total, f"{100 * r['events_6001'] / day_total:.1f}%   {r['events_6001']:,}", "blue")
             for r in rows],
            title=f"{rows[0]['model']} alone is {100 * rows[0]['events_6001'] / day_total:.0f}% of 6001 events on {latest}",
            subtitle="Each model's share of that day's 6001 events", footer=footer,
            vmax=max(10.0, 1.3 * 100 * rows[0]["events_6001"] / day_total))),
        (f"{stem}_models_top_vs_other.png", lambda: render_columns(
            [Column(d, v, f"{v:.0f}%", "blue") for d, v in zip(labels, shares)],
            title=f"The top {top} models hold {shares[-1]:.0f}% of 6001 events on {labels[-1]}",
            subtitle="Share of each day's 6001 events from the day's top models", footer=footer, vmax=100.0)),
    ]
    failures = 0
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
    parser.add_argument("--min-events", type=int, default=DEFAULT_MIN_EVENTS,
                        help="models with fewer 6001 events that day are flagged low_traffic, not hidden")
    parser.add_argument("--day-basis", choices=[b.value for b in DayBasis], default=DayBasis.IST.value)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--input", type=Path, default=None, help="enriched CSV (default: SU-4 output for the range)")
    parser.add_argument("--output-dir", type=Path, default=None, help="override the output folder (default: tenant output)")
    parser.add_argument("--no-charts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-rank-daily-top-models")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.default_start_date, config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = args.output_dir or resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    in_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    in_path = args.input or in_dir / resolver.format_range_filename(args.start_date, args.end_date, INPUT_ARTIFACT)
    basis = DayBasis(args.day_basis)
    try:
        if args.top < 1:
            raise RankModelsError(f"--top must be >= 1, got {args.top}")
        if args.min_events < 0:
            raise RankModelsError(f"--min-events must be >= 0, got {args.min_events}")
        rows = read_csv(in_path, "enriched events file (run build_enriched_events.py first)")
        validate(rows)
        by_day = assign_days(rows, basis, config.timezone, args.start_date, args.end_date)
        table = build_table(by_day, args.top, args.min_events, args.tenant, basis)
    except (RankModelsError, RankImpactedError) as exc:
        LOGGER.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    artifact = f"6001_top{args.top}_models"
    write_rows(out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact), table, FIELDS)
    failures = 0
    if not args.no_charts:
        stem = f"{args.start_date}_{args.end_date}_6001_top{args.top}"
        failures = write_charts(table, out_dir, args.tenant, basis, args.top, stem)
    print(f"tenant={args.tenant} base=events day_basis={basis.value} days={len(by_day)} "
          f"events={sum(len(v) for v in by_day.values())} rows={len(table)} chart_failures={failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
