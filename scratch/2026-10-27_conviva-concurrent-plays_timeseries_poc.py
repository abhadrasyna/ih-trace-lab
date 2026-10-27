"""POC: Conviva Concurrent Plays metric from local Athena debug events.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/concurrent-plays/
    concurrentPlay(60 s bucket) = sessions with at least one video frame in the bucket
    Concurrent Plays            = max over the selected interval of concurrentPlay

Rule used here: a session is playing from a PLAYER_STATE_CHANGE/PLAYING event until the next
BUFFERING, PAUSED, STOPPED or DESTROY state, or a PLAYER_SEEK, PLAYER_EOF or PLAYER_ERROR event. It counts in
every UTC minute its playing time overlaps. Failed attempts (never PLAYING) are excluded by construction.
A playing interval with no closing event ends at the session's last event (+ --timeout-seconds in the sensitivity view).

Args:
    --tenant           Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date             Date to analyse (YYYY-MM-DD).
    --events           Debug-events CSV (default data/athena/<tenant>/<date>_debug_all_events.csv, all event ids).
    --interval         Time-series point size in minutes (default 15, the Conviva aggregated interval).
    --timeout-seconds  Extra seconds after the last event for unclosed playing intervals in the sensitivity view (default 300).
    --out-dir          Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.
    --report-dir       Where the markdown goes (default docs/plan/conviva-metrics-recreation/concurrent-plays).
    --top              Rows in the top-content table (default 10).

Assumptions to verify: PLAYING stands in for "video frame rendered"; the end of sessions without a closing event is
estimated; the state names are ZA's debug-event vocabulary.
"""
import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.line_chart import render_line  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "investigations/ctap-smvod/data"
CLOSING_STATES = {"BUFFERING", "PAUSED", "STOPPED", "DESTROY"}
CLOSING_EVENTS = {"PLAYER_SEEK", "PLAYER_EOF", "PLAYER_ERROR"}
Event = tuple[datetime, str, str]


def read_events(path: Path) -> dict[str, list[Event]]:
    """sessionId -> time-ordered distinct (time, eventid, state); rows without a sessionId are dropped."""
    seen: set[tuple[str, str, str, str]] = set()
    out: dict[str, list[Event]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"sessionId", "eventid", "state", "datetime"} - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path}: missing columns {sorted(missing)}")
        for r in reader:
            sid = r["sessionId"].strip()
            key = (sid, r["eventid"], r["state"], r["datetime"])
            if not sid or key in seen:
                continue
            seen.add(key)
            out.setdefault(sid, []).append((datetime.strptime(r["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ"), r["eventid"], r["state"]))
    for evs in out.values():
        # Explicit tie-break so equal timestamps give the same result whatever the export's row order:
        # closing events sort before PLAYING.
        evs.sort(key=lambda e: (e[0], e[2] == "PLAYING", e[1], e[2]))
    return out


def playing_intervals(events: list[Event], extra_s: int = 0) -> list[tuple[datetime, datetime]]:
    """(start, end) while playing; an unclosed interval ends at the last event + extra_s."""
    spans, start = [], None
    for ts, eid, state in events:
        if start is not None and (state in CLOSING_STATES or eid in CLOSING_EVENTS):
            spans.append((start, ts))
            start = None
        if eid == "PLAYER_STATE_CHANGE" and state == "PLAYING" and start is None:
            start = ts
    if start is not None:
        spans.append((start, events[-1][0] + timedelta(seconds=extra_s)))
    return spans


def ends_open(events: list[Event]) -> bool:
    """True when a playing interval is still open at the session's last event (the +extra_s view extends it)."""
    return playing_intervals(events, 1) != playing_intervals(events, 0)


def alive_interval(events: list[Event]) -> list[tuple[datetime, datetime]]:
    """Whole-session view (first event to last event), the older compute_concurrent_playback.py approach."""
    return [(events[0][0], events[-1][0])]


def per_minute(spans_by_session: dict[str, list[tuple[datetime, datetime]]], day0: datetime) -> list[int]:
    """1440 counts: sessions whose spans overlap each UTC minute of the day."""
    counts = [0] * 1440
    for spans in spans_by_session.values():
        minutes: set[int] = set()
        for s, e in spans:
            lo = max(0, int((s - day0).total_seconds() // 60))
            hi = min(1439, int((e - day0).total_seconds() // 60))
            minutes.update(range(lo, hi + 1))
        for m in minutes:
            counts[m] += 1
    return counts


def interval_max(counts: list[int], size: int) -> list[int]:
    return [max(counts[i:i + size]) for i in range(0, len(counts), size)]


def peak(counts: list[int]) -> tuple[int, int]:
    """(peak value, first minute index reaching it)."""
    top = max(counts)
    return top, counts.index(top)


def sessions_at(spans_by_session: dict[str, list[tuple[datetime, datetime]]], day0: datetime, minute: int) -> set[str]:
    lo, hi = day0 + timedelta(minutes=minute), day0 + timedelta(minutes=minute + 1)
    return {sid for sid, spans in spans_by_session.items() if any(s < hi and e >= lo for s, e in spans)}


def read_session_csv(path: Path) -> dict[str, tuple[str, str, str]]:
    """sessionId -> (content title, householdId, deviceId) from the Athena session.csv."""
    out: dict[str, tuple[str, str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            sid, title = r["sessionId"].strip(), r["content"].strip()
            if sid not in out or (title and not out[sid][0]):
                out[sid] = (title, r["householdId"].strip(), r["deviceId"].strip())
    return out


def top_content(ids: set[str], info: dict[str, tuple[str, str, str]], top: int) -> tuple[list[tuple[str, int]], int]:
    titles = Counter(info[s][0] for s in ids if s in info and info[s][0])
    return sorted(titles.items(), key=lambda kv: (-kv[1], kv[0]))[:top], len(ids) - sum(titles.values())


def hhmm(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def render_report(a: argparse.Namespace, ctx: dict, chart_rel: str) -> str:
    n, tenant, day = ctx["peak"], a.tenant, a.date
    rows = "\n".join(f"| {i} | {t.replace('|', '/')} | {c:,} | {c / n:.1%} |" for i, (t, c) in enumerate(ctx["top"], 1))
    views = "\n".join(f"| {name} | {p:,} | {hhmm(m)} | {why} |" for name, p, m, why in ctx["views"])
    return f"""# Concurrent Plays — {tenant}, {day}

Generated by `scratch/2026-10-27_conviva-concurrent-plays_timeseries_poc.py`. POC output for review; not a story deliverable.

## Definition and method

Conviva ([Concurrent Plays](https://docs.conviva.ai/sei/video/metric-dictionary/concurrent-plays/)): per 60-second bucket, the active sessions with at least one video frame;
the metric is the maximum bucket value in the interval. Pause, rebuffering and seek time is not playing time, and unsuccessful attempts are excluded.

Here: playing time runs from a `PLAYING` state to the next `BUFFERING`, `PAUSED`, `STOPPED` or `DESTROY` state, or a `PLAYER_SEEK`, `PLAYER_EOF` or `PLAYER_ERROR` event.
A session counts in every UTC minute that overlaps its playing time. The chart plots the maximum per {a.interval}-minute interval; the summary is the maximum of the 1,440 minute buckets.

![Concurrent Plays]({chart_rel})

## Headline

- Concurrent Plays (day maximum): **{n:,}** at {hhmm(ctx['peak_minute'])} UTC (first minute reaching it)
- Check: the summary equals the maximum of the time-series points ({ctx['series_max']:,})
- Sessions in the events export: {ctx['sessions']:,}; reached `PLAYING`: {ctx['played']:,}; never played (failed attempts, excluded): {ctx['sessions'] - ctx['played']:,}
- Played sessions with a playing interval still open at their last event: {ctx['unclosed']:,} (the end is estimated, see the sensitivity table)

## Sensitivity and reconciliation

| View | Peak | Peak minute (UTC) | What changes |
|---|---|---|---|
{views}

## Top {len(ctx['top'])} content at the peak minute

Source: Athena `session.csv`. Percentages are of the {n:,} sessions playing in that minute.

| # | Content | Sessions | % |
|---|---|---|---|
{rows}
| | Not resolved (no title in `session.csv`) | {ctx['unresolved']:,} | {ctx['unresolved'] / n:.1%} |

## Device breakdown

Not available: `session.csv` holds only a hashed `deviceId` ({ctx['devices']:,} distinct devices and {ctx['households']:,} households among the peak-minute sessions),
no device model or OS. This is a data gap to close with the user, not something to infer.

## Known gaps and assumptions

- `PLAYING` is a proxy for "video frame rendered"; real frame data is not available.
- Conviva's inactivity limit for stale sessions is not documented in the page, so sessions with no closing event end at their last event (headline) or last event + {a.timeout_seconds}s (sensitivity).
- The local ZA data is VOD-only (`abr-vod-` session ids); linear sessions are not covered.
- The state vocabulary (`PLAYING`, `BUFFERING`, `PAUSED`, `STOPPED`, `DESTROY`, `PLAYER_SEEK`, `PLAYER_EOF`) is ZA's; other opcos must be verified.
- No Conviva reference number for this day is available to compare against.

## Reproduction

```
python scratch/2026-10-27_conviva-concurrent-plays_timeseries_poc.py --tenant {tenant} --date {day}
```

Inputs: `{ctx['events_rel']}` (Athena `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, all session events for the UTC day, pulled with the MCP ad-hoc query
that adds `PLAYER_SEEK`, `PLAYER_EOF` and `PLAYER_ERROR` to the catalog slug `ctap-smvod-debug-states`) and `data/athena/{tenant}/{day}_session.csv`.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--events", type=Path)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--timeout-seconds", type=int, default=300)
    ap.add_argument("--out-dir", type=Path, default=Path("output"))
    ap.add_argument("--report-dir", type=Path, default=Path("docs/plan/conviva-metrics-recreation/concurrent-plays"))
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    if a.interval < 1 or 1440 % a.interval:
        ap.error("--interval must divide 1440")

    athena = DATA / "athena" / a.tenant
    events_path = a.events or athena / f"{a.date}_debug_all_events.csv"
    day0 = datetime.strptime(a.date, "%Y-%m-%d")
    events = read_events(events_path)
    if not events:
        raise SystemExit(f"no events in {events_path}")

    spans = {s: playing_intervals(e) for s, e in events.items()}
    spans = {s: v for s, v in spans.items() if v}
    base = per_minute(spans, day0)
    top, pk_min = peak(base)
    if top == 0:
        raise SystemExit(f"no playing sessions on {a.date} in {events_path}; check --date and --events match")
    series = interval_max(base, a.interval)

    with_timeout = {s: playing_intervals(events[s], a.timeout_seconds) for s in spans}
    alive = {s: alive_interval(e) for s, e in events.items()}
    local_path = athena / f"{a.date}_debug_states.csv"
    local = read_events(local_path) if local_path.exists() else {}
    local_spans = {s: v for s, v in ((s, playing_intervals(e)) for s, e in local.items()) if v}
    views = [("Headline: playing time, unclosed end = last event", top, pk_min, "baseline")]
    for name, sp, why in [
        (f"Unclosed end = last event + {a.timeout_seconds}s", with_timeout, "longer end estimate for sessions with no closing event"),
        ("Session alive (first to last event)", alive, "no pause/buffer/seek exclusion and failed attempts included"),
        ("Playing time, local `debug_states.csv`", local_spans, "no seek/EOF events, only sessions in `session.csv`"),
    ]:
        if sp:
            p, m = peak(per_minute(sp, day0))
            views.append((name, p, m, why))

    info = read_session_csv(athena / f"{a.date}_session.csv")
    at_peak = sessions_at(spans, day0, pk_min)
    rows, unresolved = top_content(at_peak, info, a.top)
    unclosed = sum(1 for s in spans if ends_open(events[s]))

    xs = [day0 + timedelta(minutes=i * a.interval) for i in range(len(series))]
    png = render_line(
        xs, series,
        title=f"Concurrent Plays — {a.tenant}, {a.date}",
        kpi=("Concurrent Plays (day maximum)", f"{top:,}"),
        footer=f"Max per {a.interval} min of 60 s buckets, UTC. Base: sessions in PLAYING state (Athena debug events).",
    )
    chart = write_chart_png(png, a.out_dir, a.tenant, f"{a.date}_concurrent-plays_{a.interval}min.png")
    report = a.report_dir / f"{a.date}_{a.tenant}_concurrent-plays-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    ctx = {
        "peak": top, "peak_minute": pk_min, "series_max": max(series), "views": views, "top": rows, "unresolved": unresolved,
        "sessions": len(events), "played": len(spans), "unclosed": unclosed,
        "devices": len({info[s][2] for s in at_peak if s in info and info[s][2]}),
        "households": len({info[s][1] for s in at_peak if s in info and info[s][1]}),
        "events_rel": os.path.relpath(events_path, DATA.parent) if events_path.is_relative_to(DATA.parent) else str(events_path),
    }
    assert top == max(series), "summary must equal the maximum of the series points"
    chart_rel = Path(os.path.relpath(chart, report.parent)).as_posix()
    report.write_text(render_report(a, ctx, chart_rel), encoding="utf-8")
    print(f"chart: {chart}\nreport: {report}")
    for name, p, m, _ in views:
        print(f"{p:>5,}  {hhmm(m)}  {name}")


if __name__ == "__main__":
    main()
