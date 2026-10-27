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
import re
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


def top_content(ids: set[str], info: dict[str, tuple[str, str, str]], top: int) -> tuple[list[tuple[str, int, int]], int]:
    """(title, sessions, distinct households) for the top titles, and the number of sessions without a title."""
    titles: Counter = Counter()
    homes: dict[str, set[str]] = {}
    for s in ids:
        if s in info and info[s][0]:
            titles[info[s][0]] += 1
            if info[s][1]:
                homes.setdefault(info[s][0], set()).add(info[s][1])
    ranked = sorted(titles.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return [(t, c, len(homes.get(t, ()))) for t, c in ranked], len(ids) - sum(titles.values())


def read_setup_devices(path: Path) -> dict[str, tuple[str, str, str]]:
    """sessionId -> (OS family, browser, device class) from the parsed user agent of setupsession_with_outcome.csv."""
    out: dict[str, tuple[str, str, str]] = {}
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["sessionId"].strip(), (r["OS Family"].strip(), r["Browser Name"].strip(), r["Device Class"].strip()))
    return out


def read_drm_device_types(paths: list[Path]) -> dict[str, str]:
    """sessionId -> drmAuthToken.deviceType from the Lightstep mdrmfe exports."""
    out: dict[str, str] = {}
    for p in paths:
        with p.open(newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r.get("drmAuthToken.deviceType"):
                    out.setdefault(r["drmAuthToken.sessionId"].strip(), r["drmAuthToken.deviceType"].strip())
    return out


def breakdown(ids: set[str], labels: dict[str, str]) -> tuple[list[tuple[str, int]], int]:
    """Counts per label (descending) and the number of sessions without a label."""
    counts = Counter(labels[s] for s in ids if labels.get(s))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])), len(ids) - sum(counts.values())


def breakdown_table(title: str, rows: list[tuple[str, int]], unresolved: int, n: int) -> str:
    body = "\n".join(f"| {k.replace('|', '/')} | {c:,} | {c / n:.1%} |" for k, c in rows)
    return f"| {title} | Sessions | % |\n|---|---|---|\n{body}\n| Unresolved | {unresolved:,} | {unresolved / n:.1%} |"


def hhmm(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def render_report(a: argparse.Namespace, ctx: dict, chart_rel: str) -> str:
    n, tenant, day = ctx["peak"], a.tenant, a.date
    rows = "\n".join(f"| {i} | {t.replace('|', '/')} | {c:,} | {c / ctx['played']:.1%} | {h:,} |" for i, (t, c, h) in enumerate(ctx["top"], 1))
    return f"""# Concurrent Plays — {tenant}, {day}


## Definition

Conviva: per 60-second bucket, sessions with at least one video frame; the metric is the maximum over the interval ([doc](https://docs.conviva.ai/sei/video/metric-dictionary/concurrent-plays/)).
Here a session plays from `PLAYING` until the next `BUFFERING`, `PAUSED`, `STOPPED`, `DESTROY`, `PLAYER_SEEK`, `PLAYER_EOF` or `PLAYER_ERROR`; UTC minute buckets.

## Headline

**{n:,}** concurrent plays at {hhmm(ctx['peak_minute'])} UTC (day maximum, equal to the maximum of the series points). Of {ctx['sessions']:,} sessions, {ctx['played']:,} played and
{ctx['sessions'] - ctx['played']:,} never played (excluded); {ctx['unclosed']:,} played sessions have no closing event and end at their last event.

![Concurrent Plays]({chart_rel})

## Top {len(ctx['top'])} content by played sessions

Source: Athena session data. Percentages are of all {ctx['played']:,} sessions that played during the day.

| # | Content | Played sessions | % of played | Households |
|---|---|---|---|---|
{rows}
| | Not resolved | {ctx['unresolved']:,} | {ctx['unresolved'] / ctx['played']:.1%} | |

## Device breakdown at the peak minute

{breakdown_table('Device class / OS / browser', ctx['dev_ua'][0], ctx['dev_ua'][1], n)}

{breakdown_table('DRM device type', ctx['dev_drm'][0], ctx['dev_drm'][1], n)}

## Playback type at the peak minute

{breakdown_table('Playback type', ctx['playback'][0], ctx['playback'][1], n)}
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
    sens, recon = [("Headline: playing time, unclosed end = last event", top, pk_min, "baseline")], []
    for bucket, name, sp, why in [
        (sens, f"Unclosed end = last event + {a.timeout_seconds}s", with_timeout, "longer end estimate for sessions with no closing event"),
        (recon, "Session alive (first to last event)", alive, "no pause/buffer/seek exclusion and failed attempts included"),
        (recon, "Playing time, local `debug_states.csv`", local_spans, "no seek/EOF events, only sessions in `session.csv`"),
    ]:
        if sp:
            p, m = peak(per_minute(sp, day0))
            bucket.append((name, p, m, why))

    info = read_session_csv(athena / f"{a.date}_session.csv")
    at_peak = sessions_at(spans, day0, pk_min)
    rows, unresolved = top_content(set(spans), info, a.top)
    unclosed = sum(1 for s in spans if ends_open(events[s]))
    ua = read_setup_devices(DATA.parent / "output" / a.tenant / f"{a.date}_setupsession_with_outcome.csv")
    ua_labels = {s: " / ".join(x or "?" for x in (d[2], d[0], d[1])) for s, d in ua.items() if any(d)}
    drm_files = sorted((DATA / "lightstep" / a.tenant).glob(f"{a.date}_*mdrmfe.csv"))
    drm_labels = read_drm_device_types(drm_files)

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
        "peak": top, "peak_minute": pk_min, "series_max": max(series), "top": rows, "unresolved": unresolved,
        "sessions": len(events), "played": len(spans), "unclosed": unclosed,
        "dev_ua": breakdown(at_peak, ua_labels), "dev_drm": breakdown(at_peak, drm_labels),
        "playback": breakdown(at_peak, {s: (re.match(r"abr-([a-z]+)-", s) or [None, ""])[1].upper() for s in at_peak}),
    }
    assert top == max(series), "summary must equal the maximum of the series points"
    chart_rel = Path(os.path.relpath(chart, report.parent)).as_posix()
    report.write_text(render_report(a, ctx, chart_rel), encoding="utf-8")
    print(f"chart: {chart}\nreport: {report}")
    for name, p, m, _ in sens + recon:
        print(f"{p:>5,}  {hhmm(m)}  {name}")


if __name__ == "__main__":
    main()
