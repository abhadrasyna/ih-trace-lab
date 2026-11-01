"""Probe: derive smvod-ts oldest/youngest micros from smvod query_timeseries points and compare with the hand CSV (LX-1 follow-up).

Usage: python3 scratch/2026-11-01_lightstep_smvod-ts_derive_probe.py --tenant ZA --date 2026-09-28
Fetches the smvod query at output-period 1 s per slice, takes each series' first/last non-zero point
timestamp as oldest/youngest, and compares per sessionId with <date>_smvod-ts.csv. Token never printed.
"""
import argparse
import csv
import importlib.util
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("lx1", ROOT / "scratch/2026-11-01_lightstep_export_api_feasibility_probe.py")
lx1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lx1)


def fetch_series(ctx: dict, query: str, start: datetime, end: datetime, period: int, calls: list) -> list:
    """Raw series for a window at a fixed output period; halves the window on >= 50 series."""
    for _ in range(5):
        status, resp, _dt = lx1.post(ctx["region"], ctx["project"], lx1.build_body(query, start, end, period))
        calls.append(status)
        if status == 200:
            break
        if status not in (429, 599) and status < 500:
            raise SystemExit(f"HTTP {status}: {resp}")
    else:
        raise SystemExit(f"retries exhausted, statuses {calls[-5:]}")
    series = resp["data"]["attributes"].get("series", [])
    if len(series) >= 50:
        if (end - start).total_seconds() <= period:
            raise SystemExit(f"still >= 50 series in a {period}s window at {start}")
        mid = start + (end - start) / 2
        return fetch_series(ctx, query, start, mid, period, calls) + fetch_series(ctx, query, mid, end, period, calls)
    return series


def span_bounds(series: list) -> dict:
    """sessionId -> (first_ms, last_ms) over non-zero points of every series with that sessionId."""
    out: dict = {}
    for s in series:
        labels = dict(x.split("=", 1) for x in s["group-labels"])
        sid = labels.get("sessionId", "")
        ts = [p[0] for p in s["points"] if p[1]]
        if not ts:
            continue
        lo, hi = min(ts), max(ts)
        old = out.get(sid)
        out[sid] = (lo, hi) if old is None else (min(old[0], lo), max(old[1], hi))
    return out


def read_hand(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {r["sessionId"]: (int(r["oldest_micros"]) / 1000, int(r["youngest_micros"]) / 1000, float(r["duration_millis"])) for r in rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--hours", type=int, default=1)
    ap.add_argument("--period", type=int, default=1, help="output period seconds")
    a = ap.parse_args()
    if a.hours < 1 or 24 % a.hours:
        raise SystemExit("--hours must be a divisor of 24")
    lx1.load_env()
    ctx = lx1.resolve("lightstep_go", a.tenant)
    day = datetime.strptime(a.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    calls: list = []
    series: list = []
    for h in range(0, 24, a.hours):
        series += fetch_series(ctx, lx1.UQL["smvod"], day + timedelta(hours=h), day + timedelta(hours=h + a.hours), a.period, calls)
    derived = span_bounds(series)
    hand = read_hand(ROOT / f"investigations/ctap-smvod/data/lightstep/{a.tenant}/{a.date}_smvod-ts.csv")
    both = set(derived) & set(hand)
    print(f"calls={len(calls)} series={len(series)} derived_sessions={len(derived)} hand_sessions={len(hand)} "
          f"both={len(both)} only_derived={len(set(derived) - set(hand))} only_hand={len(set(hand) - set(derived))}")
    if not both:
        return
    d_old = [derived[s][0] - hand[s][0] for s in both]
    d_young = [derived[s][1] - hand[s][1] for s in both]
    for name, d in (("oldest", d_old), ("youngest", d_young)):
        print(f"{name}: derived-hand ms min={min(d):.0f} median={statistics.median(d):.0f} max={max(d):.0f} "
              f"within_period={sum(0 <= x <= a.period * 1000 for x in d)}/{len(d)}")
    dur = [hand[s][2] for s in both]
    print(f"hand duration_millis: min={min(dur):.1f} median={statistics.median(dur):.1f} max={max(dur):.1f} "
          f"(not derivable from point timestamps; period={a.period}s)")
    for s in list(set(hand) - set(derived))[:3]:
        print("  only_hand:", s)
    for s in list(set(derived) - set(hand))[:3]:
        print("  only_derived:", s)


if __name__ == "__main__":
    sys.exit(main())
