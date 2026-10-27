"""POC: Conviva CIR Related Exits metric from local Athena debug events.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/cir-related-exits/
    CIRRelatedExit(session) = 1 when the session is an ended play and CIR occurred within 5 s of its end
    CIR Related Exits       = sum(CIRRelatedExit) / sum(endedPlay) over the interval

Rules used here (assumptions to verify, not Conviva facts):
- Ended play: a session with at least one PLAYING state and a terminal DESTROY, STOPPED or PLAYER_ERROR event after it
  (errors count as ended plays, user decision 2026-10-27). The session end is the first such event.
- A stall is BUFFERING after the first PLAYING until the next PLAYING or PAUSED (or the session end, if still open).
  The startup BUFFERING before the first PLAYING is not a stall.
- A stall that starts less than --seek-grace-seconds after a PLAYER_SEEK is seek-induced (not CIR); otherwise it is CIR
  (the 10 s rule is from Conviva's CIRR page, applied here by user decision). PLAYER_SEEK carries only a start time.
- The play counts as a CIR related exit when a CIR stall overlaps the last --window-seconds before the session end
  (a stall still open at the end counts). Each play is bucketed by its end time (UTC).
- Not modelled: the 30 s impact period, the 90 s expiry, sessions under 30 s, backgrounding as session end.

Args:
    --tenant           Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date             Date to analyse (YYYY-MM-DD).
    --events           Debug-events CSV (default data/athena/<tenant>/<date>_debug_all_events.csv).
    --interval         Time-series point size in minutes (default 5).
    --window-seconds   CIR-to-end window (default 5, the Conviva rule).
    --seek-grace-seconds  Stall start within this time after a seek is not CIR (default 10).
    --out-dir          Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.
    --report-dir       Where the markdown goes (default docs/plan/conviva-metrics-recreation/cir-related-exits).
    --top              Rows in the top-content table (default 10).

Reuses the readers and tables of the concurrent plays POC (second use of this plumbing; share them when formalised).
"""
import argparse
import importlib.util
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.line_chart import render_line  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402

_spec = importlib.util.spec_from_file_location("cp_poc", Path(__file__).with_name("2026-10-27_conviva-concurrent-plays_timeseries_poc.py"))
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

TERMINAL_STATES = {"DESTROY", "STOPPED"}
Event = tuple[datetime, str, str]


def analyse_session(events: list[Event], window_s: float, grace_s: float) -> tuple[datetime, bool] | None:
    """(session end, is CIR related exit) for an ended play, or None when the session never played or never ended."""
    play = next((i for i, (_, e, s) in enumerate(events) if e == "PLAYER_STATE_CHANGE" and s == "PLAYING"), None)
    if play is None:
        return None
    end_i = next((i for i in range(play, len(events))
                  if events[i][2] in TERMINAL_STATES or events[i][1] == "PLAYER_ERROR"), None)
    if end_i is None:
        return None
    end = events[end_i][0]
    seeks = [t for t, e, _ in events[play:end_i] if e == "PLAYER_SEEK"]
    stalls, start = [], None
    for ts, eid, state in events[play:end_i]:
        if eid != "PLAYER_STATE_CHANGE":
            continue
        if state == "BUFFERING" and start is None:
            start = ts
        elif state in {"PLAYING", "PAUSED"} and start is not None:
            stalls.append((start, ts))
            start = None
    if start is not None:
        stalls.append((start, end))
    cutoff = end - timedelta(seconds=window_s)
    for s, e in stalls:
        seek_induced = any(0 <= (s - k).total_seconds() < grace_s for k in seeks)
        if not seek_induced and e >= cutoff:
            return end, True
    return end, False


def bucket_rates(ends: list[tuple[datetime, bool]], day0: datetime, size: int) -> tuple[list[int], list[int]]:
    """(ended plays, CIR related exits) per `size`-minute UTC bucket of the day."""
    n = 1440 // size
    ended, flagged = [0] * n, [0] * n
    for end, flag in ends:
        i = int((end - day0).total_seconds() // (size * 60))
        if 0 <= i < n:
            ended[i] += 1
            flagged[i] += flag
    return ended, flagged


def render_report(a: argparse.Namespace, ctx: dict, chart_rel: str) -> str:
    n = ctx["flagged"]
    rows = "\n".join(f"| {i} | {t.replace('|', '/')} | {c:,} | {c / n:.1%} | {h:,} |" for i, (t, c, h) in enumerate(ctx["top"], 1))
    return f"""# CIR Related Exits — {a.tenant}, {a.date}

## Definition

Conviva: ended plays with connection-induced rebuffering (CIR) within 5 seconds of the session end, divided by ended plays
([doc](https://docs.conviva.ai/sei/video/metric-dictionary/cir-related-exits/)).

- Stall: `BUFFERING` after the first `PLAYING`; CIR unless it starts less than {a.seek_grace_seconds:g} s after a `PLAYER_SEEK`.
- Counts when a CIR stall overlaps the last {a.window_seconds:g} s of the play.
- Ended play: played, then `DESTROY`, `STOPPED` or `PLAYER_ERROR`; UTC buckets by session end.

## Headline

**{ctx['rate']:.2%}** of ended plays were CIR related exits: {n:,} of {ctx['ended']:,}. Of {ctx['sessions']:,} sessions, {ctx['sessions'] - ctx['ended'] - ctx['other_day']:,} are not ended plays (never played, or no end event) and {ctx['other_day']:,} ended on another UTC day.

![CIR Related Exits]({chart_rel})

## Top {len(ctx['top'])} content of CIR related exits

Percentages are of all {n:,} CIR related exits.

| # | Content | Exits | % of exits | Households |
|---|---|---|---|---|
{rows}
| | Not resolved | {ctx['unresolved']:,} | {ctx['unresolved'] / n:.1%} | |

## Device breakdown of CIR related exits

{cp.breakdown_table('Device class / OS / browser', ctx['dev_ua'][0], ctx['dev_ua'][1], n)}

{cp.breakdown_table('DRM device type', ctx['dev_drm'][0], ctx['dev_drm'][1], n)}

## Playback type of CIR related exits

{cp.breakdown_table('Playback type', ctx['playback'][0], ctx['playback'][1], n)}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--events", type=Path)
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--window-seconds", type=float, default=5)
    ap.add_argument("--seek-grace-seconds", type=float, default=10)
    ap.add_argument("--out-dir", type=Path, default=Path("output"))
    ap.add_argument("--report-dir", type=Path, default=Path("docs/plan/conviva-metrics-recreation/cir-related-exits"))
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    if a.interval < 1 or 1440 % a.interval:
        ap.error("--interval must divide 1440")

    athena = cp.DATA / "athena" / a.tenant
    events_path = a.events or athena / f"{a.date}_debug_all_events.csv"
    day0 = datetime.strptime(a.date, "%Y-%m-%d")
    events = cp.read_events(events_path)
    if not events:
        raise SystemExit(f"no events in {events_path}")

    day1 = day0 + timedelta(days=1)
    analysed = {s: analyse_session(e, a.window_seconds, a.seek_grace_seconds) for s, e in events.items()}
    all_ended = {s: r for s, r in analysed.items() if r}
    results = {s: r for s, r in all_ended.items() if day0 <= r[0] < day1}
    other_day = len(all_ended) - len(results)
    if not results:
        raise SystemExit(f"no ended plays on {a.date} in {events_path}; check --date and --events match")
    ended, flagged = bucket_rates([r for r in results.values()], day0, a.interval)
    total_ended, total_flagged = sum(ended), sum(flagged)
    if total_flagged == 0:
        raise SystemExit("no CIR related exits found; check the event vocabulary")
    rate = total_flagged / total_ended
    series = [100 * f / e if e else 0.0 for e, f in zip(ended, flagged)]
    if total_ended != len(results):
        raise SystemExit("ended plays do not reconcile with the bucketed series")

    exit_ids = {s for s, (_, f) in results.items() if f}
    info = cp.read_session_csv(athena / f"{a.date}_session.csv")
    rows, unresolved = cp.top_content(exit_ids, info, a.top)
    ua = cp.read_setup_devices(cp.DATA.parent / "output" / a.tenant / f"{a.date}_setupsession_with_outcome.csv")
    ua_labels = {s: " / ".join(x or "?" for x in (d[2], d[0], d[1])) for s, d in ua.items() if any(d)}
    drm_labels = cp.read_drm_device_types(sorted((cp.DATA / "lightstep" / a.tenant).glob(f"{a.date}_*mdrmfe.csv")))

    xs = [day0 + timedelta(minutes=i * a.interval) for i in range(len(series))]
    png = render_line(
        xs, series,
        title=f"CIR Related Exits — {a.tenant}, {a.date}",
        kpi=("CIR Related Exits (day)", f"{rate:.2%}  ({total_flagged:,} of {total_ended:,} ended plays)"),
        footer=f"% of ended plays per {a.interval} min bucket by session end, UTC. CIR within {a.window_seconds:g} s of end (Athena debug events).",
    )
    chart = write_chart_png(png, a.out_dir, a.tenant, f"{a.date}_cir-related-exits_{a.interval}min.png")
    report = a.report_dir / f"{a.date}_{a.tenant}_cir-related-exits-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    ctx = {
        "rate": rate, "flagged": total_flagged, "ended": total_ended, "sessions": len(events), "other_day": other_day, "top": rows, "unresolved": unresolved,
        "dev_ua": cp.breakdown(exit_ids, ua_labels), "dev_drm": cp.breakdown(exit_ids, drm_labels),
        "playback": cp.breakdown(exit_ids, {s: (re.match(r"abr-([a-z]+)-", s) or [None, ""])[1].upper() for s in exit_ids}),
    }
    chart_rel = Path(os.path.relpath(chart, report.parent)).as_posix()
    report.write_text(render_report(a, ctx, chart_rel), encoding="utf-8")
    print(f"chart: {chart}\nreport: {report}\nended plays {total_ended:,}, CIR related exits {total_flagged:,} ({rate:.2%})")


if __name__ == "__main__":
    main()
