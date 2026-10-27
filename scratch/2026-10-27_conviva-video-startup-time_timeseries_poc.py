"""POC: Conviva Video Startup Time (VST) metric from local Athena debug events; compares with session.csv startup_time_ms.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/video-startup-time/
    VST(session) = timestamp(playStart) - timestamp(attempt)   (minus pre-roll ad time when there is one)
    VST          = Average(VST(session)) over the plays starting in the interval; capped at 600 s per play

Rules used here (assumptions to verify, not Conviva facts):
- attempt = the session's CREATE event; playStart = its first PLAYING state. Only plays (sessions with a PLAYING) count.
- Plays are bucketed by attempt time (user decision 2026-10-27), UTC day; a session whose attempt is on another day is dropped.
- Pre-roll ads: none modelled (no ad events in the data; assumed absent for VOD). Heartbeat-gap exclusion and revived
  sessions: not modelled, there is no equivalent field.
- The cap (default 600 s) is applied per play; VST below zero is dropped and counted.
- Comparison only (stdout): the same plays' session.csv `startup_time_ms` (REQUEST_VIEWING, per merge_session_outcome.py).

Args:
    --tenant      Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date        Date to analyse (YYYY-MM-DD).
    --events      Debug-events CSV (default data/athena/<tenant>/<date>_debug_all_events.csv).
    --interval    Time-series point size in minutes (default 5).
    --cap-seconds Per-play VST cap (default 600, the Conviva rule).
    --out-dir     Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.
    --report-dir  Where the markdown goes (default docs/plan/conviva-metrics-recreation/video-startup-time).
    --top         Rows in the top-content table (default 10).

Reuses the readers and tables of the concurrent plays POC (third use of this plumbing; share them when formalised).
"""
import argparse
import csv
import importlib.util
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.line_chart import render_line  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402

_spec = importlib.util.spec_from_file_location("cp_poc", Path(__file__).with_name("2026-10-27_conviva-concurrent-plays_timeseries_poc.py"))
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

BINS = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 10), (10, 30), (30, 60), (60, 600), (600, None)]
Event = tuple[datetime, str, str]


def startup(events: list[Event]) -> tuple[datetime, float] | None:
    """(attempt time, uncapped seconds to the first PLAYING) for a played session, else None."""
    create = next((t for t, e, s in events if e == "PLAYER_SESSION_EVENT" and s == "CREATE"), None)
    play = next((t for t, e, s in events if e == "PLAYER_STATE_CHANGE" and s == "PLAYING"), None)
    if create is None or play is None:
        return None
    return create, (play - create).total_seconds()


def bucket_average(plays: list[tuple[datetime, float]], day0: datetime, size: int) -> list[float | None]:
    """Average VST (s) per `size`-minute UTC bucket of the attempt time; None for empty buckets."""
    n = 1440 // size
    sums, counts = [0.0] * n, [0] * n
    for t, v in plays:
        i = int((t - day0).total_seconds() // (size * 60))
        if 0 <= i < n:
            sums[i] += v
            counts[i] += 1
    return [s / c if c else None for s, c in zip(sums, counts)]


def counts_per_bucket(plays: list[tuple[datetime, float]], day0: datetime, size: int) -> list[int]:
    counts = [0] * (1440 // size)
    for t, _ in plays:
        counts[int((t - day0).total_seconds() // (size * 60))] += 1
    return counts


def distribution(values: list[float]) -> list[tuple[str, int]]:
    out = []
    for lo, hi in BINS:
        label = f"{lo}-{hi} s" if hi else f">= {lo} s"
        out.append((label, sum(1 for v in values if v >= lo and (hi is None or v < hi))))
    return out


def group_table(title: str, ids: dict[str, float], labels: dict[str, str], top: int | None = None) -> str:
    groups: dict[str, list[float]] = defaultdict(list)
    for s, v in ids.items():
        groups[labels.get(s) or ""].append(v)
    rows = sorted(((k, vs) for k, vs in groups.items() if k), key=lambda kv: (-len(kv[1]), kv[0]))[:top]
    lines = [f"| {title} | Plays | Avg VST (s) |", "|---|---|---|"]
    lines += [f"| {k.replace('|', '/')} | {len(vs):,} | {sum(vs) / len(vs):.2f} |" for k, vs in rows]
    un = groups.get("", [])
    lines.append(f"| Unresolved | {len(un):,} | {sum(un) / len(un):.2f} |" if un else "| Unresolved | 0 | |")
    return "\n".join(lines)


def render_report(a: argparse.Namespace, ctx: dict, chart_rel: str) -> str:
    dist = "\n".join(f"| {k} | {c:,} | {c / ctx['plays']:.1%} |" for k, c in ctx["dist"])
    return f"""# Video Startup Time — {a.tenant}, {a.date}

## Definition

Conviva: time from the play attempt to the first frame displayed, averaged over the plays starting in the interval; capped at {a.cap_seconds:g} s per play
([doc](https://docs.conviva.ai/sei/video/metric-dictionary/video-startup-time/)).

- Attempt = `CREATE`; first frame = first `PLAYING`. Plays are bucketed by attempt time, UTC.
- No pre-roll ads or heartbeat gaps are modelled.

## Headline

**{ctx['avg']:.2f} s** average VST over {ctx['plays']:,} plays (median {ctx['median']:.2f} s, 90th percentile {ctx['p90']:.2f} s). Capped at the limit: {ctx['capped']:,}.
Of {ctx['sessions']:,} sessions, {ctx['never_played']:,} never played, {ctx['other_day']:,} had their attempt on another UTC day and {ctx['unusable']:,} had no usable attempt time.

![Video Startup Time]({chart_rel})

## Distribution

| VST | Plays | % of plays |
|---|---|---|
{dist}

## Top {a.top} content by plays

{ctx['top_table']}

## Device breakdown

{ctx['dev_ua']}

{ctx['dev_drm']}

## Playback type

{ctx['playback']}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--events", type=Path)
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--cap-seconds", type=float, default=600)
    ap.add_argument("--out-dir", type=Path, default=Path("output"))
    ap.add_argument("--report-dir", type=Path, default=Path("docs/plan/conviva-metrics-recreation/video-startup-time"))
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    if a.interval < 1 or 1440 % a.interval:
        ap.error("--interval must divide 1440")

    athena = cp.DATA / "athena" / a.tenant
    events_path = a.events or athena / f"{a.date}_debug_all_events.csv"
    day0 = datetime.strptime(a.date, "%Y-%m-%d")
    day1 = day0 + timedelta(days=1)
    events = cp.read_events(events_path)
    if not events:
        raise SystemExit(f"no events in {events_path}")

    raw = {s: r for s, e in events.items() if (r := startup(e))}
    on_day = {s: r for s, r in raw.items() if day0 <= r[0] < day1}
    other_day = len(raw) - len(on_day)
    played = sum(1 for e in events.values() if any(ev == "PLAYER_STATE_CHANGE" and st == "PLAYING" for _, ev, st in e))
    negative = [s for s, (_, v) in on_day.items() if v < 0]
    unusable = (played - len(raw)) + len(negative)
    never_played = len(events) - played
    vst = {s: min(v, a.cap_seconds) for s, (_, v) in on_day.items() if v >= 0}
    if not vst:
        raise SystemExit(f"no plays with CREATE and PLAYING on {a.date} in {events_path}; check --date and --events match")
    capped = sum(1 for s in vst if on_day[s][1] > a.cap_seconds)
    plays = [(on_day[s][0], v) for s, v in vst.items()]
    values = sorted(vst.values())
    avg = sum(values) / len(values)
    series = bucket_average(plays, day0, a.interval)
    if sum(counts_per_bucket(plays, day0, a.interval)) != len(vst) or len(vst) + never_played + other_day + unusable != len(events):
        raise SystemExit("plays do not reconcile with the bucketed series and session totals")

    info = cp.read_session_csv(athena / f"{a.date}_session.csv")
    titles = {s: info[s][0] for s in vst if s in info}
    ua = cp.read_setup_devices(cp.DATA.parent / "output" / a.tenant / f"{a.date}_setupsession_with_outcome.csv")
    ua_labels = {s: " / ".join(x or "?" for x in (d[2], d[0], d[1])) for s, d in ua.items() if any(d)}
    drm_labels = cp.read_drm_device_types(sorted((cp.DATA / "lightstep" / a.tenant).glob(f"{a.date}_*mdrmfe.csv")))
    playback = {s: (re.match(r"abr-([a-z]+)-", s) or [None, ""])[1].upper() for s in vst}

    xs = [day0 + timedelta(minutes=i * a.interval) for i in range(len(series))]
    ys = [v for v in series]
    png = render_line(
        [x for x, y in zip(xs, ys) if y is not None], [y for y in ys if y is not None],
        title=f"Video Startup Time — {a.tenant}, {a.date}",
        kpi=("Video Startup Time (day average)", f"{avg:.2f} s  ({len(vst):,} plays)"),
        footer=f"Average seconds, attempt to first frame, per {a.interval} min bucket by attempt time, UTC (Athena debug events).",
    )
    chart = write_chart_png(png, a.out_dir, a.tenant, f"{a.date}_video-startup-time_{a.interval}min.png")
    report = a.report_dir / f"{a.date}_{a.tenant}_video-startup-time-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    ctx = {
        "avg": avg, "median": statistics.median(values), "p90": values[int(0.9 * (len(values) - 1))], "plays": len(vst), "capped": capped,
        "sessions": len(events), "other_day": other_day, "never_played": never_played, "unusable": unusable, "dist": distribution(values),
        "top_table": group_table("Content", vst, titles, a.top), "dev_ua": group_table("Device class / OS / browser", vst, ua_labels),
        "dev_drm": group_table("DRM device type", vst, drm_labels), "playback": group_table("Playback type", vst, playback),
    }
    chart_rel = Path(os.path.relpath(chart, report.parent)).as_posix()
    report.write_text(render_report(a, ctx, chart_rel), encoding="utf-8")

    # Comparison with the session.csv startup_time_ms column (stdout only, not in the report).
    ms = {}
    with (athena / f"{a.date}_session.csv").open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                ms[r["sessionId"].strip()] = float(r["startup_time_ms"]) / 1000
            except ValueError:
                continue
    both = [s for s in vst if s in ms]
    diffs = sorted(ms[s] - on_day[s][1] for s in both)
    print(f"chart: {chart}\nreport: {report}")
    print(f"plays {len(vst):,}, avg VST {avg:.2f} s, median {ctx['median']:.2f} s, capped {capped}, negative dropped {len(negative)}, other-day {other_day}")
    if both:
        csv_avg = sum(min(ms[s], a.cap_seconds) for s in both) / len(both)
        print(f"session.csv startup_time_ms on {len(both):,} of the plays: avg {csv_avg:.2f} s vs debug-delta {sum(vst[s] for s in both) / len(both):.2f} s; "
              f"median diff (csv - delta) {statistics.median(diffs):.2f} s, p10 {diffs[len(diffs) // 10]:.2f}, p90 {diffs[9 * len(diffs) // 10]:.2f}")
    if ms:
        all_ms = sorted(min(v, a.cap_seconds) for v in ms.values())
        print(f"session.csv startup_time_ms over ALL {len(all_ms):,} sessions: avg {sum(all_ms) / len(all_ms):.2f} s, median {statistics.median(all_ms):.2f} s")


if __name__ == "__main__":
    main()
