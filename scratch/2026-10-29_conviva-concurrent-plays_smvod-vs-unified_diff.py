"""Overlay + diff: Concurrent Plays from SM-vod debug events vs unified_sessions (session.csv), one tenant/day.

SM-vod series   : PLAYING until a closing event, from <date>_debug_all_events.csv (same rule as the POC).
Unified series  : session.csv event_start -> event_end (unified_sessions), rows without both are dropped, no estimate.

Writes an overlay PNG (15 min max of 60 s buckets) and a diff-only markdown (peaks, session-set diff, largest gaps).

Args:
    --tenant      Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date        Date to analyse (YYYY-MM-DD).
    --interval    Series point size in minutes (default 15).
    --top-gaps    Rows in the largest-gap table (default 10).
    --out-dir     Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.
    --report-dir  Markdown folder (default docs/plan/conviva-metrics-recreation/concurrent-plays).
"""
import argparse
import csv
import importlib.util
import os
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("poc", HERE / "2026-10-27_conviva-concurrent-plays_timeseries_poc.py")
poc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poc)

Spans = dict[str, list[tuple[datetime, datetime]]]


def unified_spans(path: Path) -> tuple[Spans, int]:
    """sessionId -> [(event_start, event_end)] for rows with both; also the number of rows dropped."""
    out: Spans = {}
    dropped = 0
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            s, e = r["event_start"].strip(), r["event_end"].strip()
            sid = r["sessionId"].strip()
            if not sid or not s or not e:
                dropped += 1
                continue
            fmt = "%Y-%m-%d %H:%M:%S.%f"
            start, end = datetime.strptime(s, fmt), datetime.strptime(e, fmt)
            if end < start:
                dropped += 1
                continue
            out.setdefault(sid, []).append((start, end))
    return out, dropped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--top-gaps", type=int, default=10)
    ap.add_argument("--out-dir", type=Path, default=Path("output"))
    ap.add_argument("--report-dir", type=Path, default=Path("docs/plan/conviva-metrics-recreation/concurrent-plays"))
    a = ap.parse_args()
    if a.interval < 1 or 1440 % a.interval:
        ap.error("--interval must divide 1440")

    athena = poc.DATA / "athena" / a.tenant
    day0 = datetime.strptime(a.date, "%Y-%m-%d")
    events = poc.read_events(athena / f"{a.date}_debug_all_events.csv")
    sm = {s: v for s, v in ((s, poc.playing_intervals(e)) for s, e in events.items()) if v}
    uni, dropped = unified_spans(athena / f"{a.date}_session.csv")
    if not sm or not uni:
        raise SystemExit("one of the series is empty; check inputs")

    sm_min, uni_min = poc.per_minute(sm, day0), poc.per_minute(uni, day0)
    sm_ser, uni_ser = poc.interval_max(sm_min, a.interval), poc.interval_max(uni_min, a.interval)
    xs = [day0 + timedelta(minutes=i * a.interval) for i in range(len(sm_ser))]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(xs, sm_ser, label=f"SM-vod (debug events), max {max(sm_ser)}", color="#1f77b4", lw=1.8)
    ax.plot(xs, uni_ser, label=f"Unified session (session.csv), max {max(uni_ser)}", color="#ff7f0e", lw=1.8)
    ax.fill_between(xs, sm_ser, uni_ser, color="grey", alpha=0.2, label="difference")
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_title(f"Concurrent Plays: SM-vod vs unified session — {a.tenant}, {a.date}")
    ax.set_ylabel(f"max per {a.interval} min of 60 s buckets (UTC)")
    ax.legend()
    ax.grid(alpha=0.3)
    chart = a.out_dir / a.tenant / "charts" / f"{a.date}_concurrent-plays_smvod-vs-unified_{a.interval}min.png"
    chart.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chart, dpi=130, bbox_inches="tight")

    sm_pk, sm_pm = poc.peak(sm_min)
    un_pk, un_pm = poc.peak(uni_min)
    only_sm, only_un, both = set(sm) - set(uni), set(uni) - set(sm), set(sm) & set(uni)
    delta = [s - u for s, u in zip(sm_min, uni_min, strict=True)]
    gaps = sorted(range(len(delta)), key=lambda m: -abs(delta[m]))[: a.top_gaps]
    gap_rows = "\n".join(f"| {poc.hhmm(m)} | {sm_min[m]} | {uni_min[m]} | {delta[m]:+d} |" for m in sorted(gaps))
    mean_abs = sum(abs(d) for d in delta) / len(delta)
    total = sum(delta)
    verdict = "the SM-vod series is higher overall" if total > 0 else "the unified series is higher overall" if total < 0 else "the series tie overall"

    report = a.report_dir / f"{a.date}_{a.tenant}_concurrent-plays_smvod-vs-unified-diff.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    rel = Path(os.path.relpath(chart, report.parent)).as_posix()
    report.write_text(f"""# Concurrent Plays, SM-vod vs unified session — {a.tenant}, {a.date}

![overlay]({rel})

## Summary

- Peak: SM-vod **{sm_pk}** at {poc.hhmm(sm_pm)} UTC vs unified **{un_pk}** at {poc.hhmm(un_pm)} UTC (difference {sm_pk - un_pk:+d}).
- Mean absolute per-minute difference {mean_abs:.2f}; {verdict} (sum of per-minute difference {total:+,}).
- Sessions: {len(sm):,} played in SM-vod, {len(uni):,} in unified (complete start and end); {len(both):,} in both,
  {len(only_sm):,} only SM-vod, {len(only_un):,} only unified. {dropped:,} unified rows dropped (no sessionId, event_start or event_end, or end before start).
- SM-vod counts time from PLAYING to the next closing event; unified counts event_start to event_end, so it includes startup/buffering/paused time and drops sessions without an end.

## Largest per-minute gaps (SM-vod minus unified)

| UTC minute | SM-vod | Unified | Difference |
|---|---|---|---|
{gap_rows}
""", encoding="utf-8")
    print(f"chart: {chart}\nreport: {report}")
    print(f"peak sm={sm_pk}@{poc.hhmm(sm_pm)} uni={un_pk}@{poc.hhmm(un_pm)} both={len(both)} only_sm={len(only_sm)} only_uni={len(only_un)}")


if __name__ == "__main__":
    main()
