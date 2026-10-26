"""POC: Conviva Attempts metric time series (attempts per minute) from local Athena data.

Purpose: build a per-minute Attempts series from CREATE events in the local Athena
``debug_states.csv``, plot it to PNG, and reconcile the totals against ``session.csv``
and the Lightstep smvod session counts.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/attempts/

Args:
    --tenant    Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date      Date to analyse (YYYY-MM-DD).
    --interval  Bucket size in whole minutes (default 5).
    --out-dir   Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.

Assumption (to verify): one Attempt = one distinct sessionId with a PLAYER_SESSION_EVENT/CREATE
event, bucketed by the CREATE timestamp (UTC). Conviva's formula image is not readable from the docs.
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.line_chart import render_line  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "investigations/ctap-smvod/data"


def read_create_times(path: Path) -> dict[str, datetime]:
    """First CREATE timestamp per sessionId."""
    first: dict[str, datetime] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["eventid"] == "PLAYER_SESSION_EVENT" and row["state"] == "CREATE":
                ts = datetime.strptime(row["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ")
                sid = row["sessionId"]
                if sid not in first or ts < first[sid]:
                    first[sid] = ts
    return first


def bucket(times: list[datetime], minutes: int) -> Counter:
    step = timedelta(minutes=minutes)
    return Counter(datetime.min + ((t - datetime.min) // step) * step for t in times)


def distinct_ids(path: Path, column: str) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if column not in (reader.fieldnames or []):
            raise SystemExit(f"{path}: no '{column}' column (has {reader.fieldnames})")
        return {r[column] for r in reader if r[column]}


def series_points(series: Counter, minutes: int) -> tuple[list[datetime], list[int]]:
    """Zero-filled (bucket start, count) points from first to last bucket."""
    step = timedelta(minutes=minutes)
    xs, t = [], min(series)
    while t <= max(series):
        xs.append(t)
        t += step
    return xs, [series.get(x, 0) for x in xs]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--interval", type=int, default=5, help="bucket size in minutes")
    ap.add_argument("--out-dir", type=Path, default=Path("output"), help="charts go to <out-dir>/<tenant>/charts/")
    args = ap.parse_args()
    if args.interval < 1:
        ap.error("--interval must be >= 1")

    athena = DATA / "athena" / args.tenant
    creates = read_create_times(athena / f"{args.date}_debug_states.csv")
    day = args.date
    creates = {s: t for s, t in creates.items() if t.date().isoformat() == day}
    if not creates:
        raise SystemExit(f"no CREATE events for {args.tenant} on {day}")
    series = bucket(list(creates.values()), args.interval)
    total = sum(series.values())

    out_dir = args.out_dir
    xs, ys = series_points(series, args.interval)
    png = render_line(
        xs,
        ys,
        title=f"Attempts — {args.tenant}, {args.date}",
        subtitle=f"{total:,} attempts (sum of points), per {args.interval} min, UTC; base: distinct sessionId with CREATE",
    )
    out = write_chart_png(png, out_dir, args.tenant, f"{args.date}_attempts_{args.interval}min.png")

    sessions = distinct_ids(athena / f"{args.date}_session.csv", "sessionId")
    outcome = distinct_ids(athena / f"{args.date}_outcome_first_debug.csv", "sessionId")
    ls_path = DATA / "lightstep" / args.tenant / f"{args.date}_smvod.csv"
    ls = distinct_ids(ls_path, "sessionId") if ls_path.exists() else None

    first, last = min(creates.values()), max(creates.values())
    print(f"chart: {out}")
    print(f"CREATE window (UTC): {first} .. {last}")
    print(f"attempts = sum of series : {total}")
    print(f"session.csv sessions     : {len(sessions)}  (CREATE not in it: {len(set(creates) - sessions)}, it not in CREATE: {len(sessions - set(creates))})")
    print(f"outcome_first_debug      : {len(outcome)}  (CREATE not in it: {len(set(creates) - outcome)})")
    if ls is None:
        print(f"lightstep smvod sessions : file not found ({ls_path})")
    else:
        print(f"lightstep smvod sessions : {len(ls)}  (CREATE not in it: {len(set(creates) - ls)})")


if __name__ == "__main__":
    main()
