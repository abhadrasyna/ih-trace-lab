"""POC: Conviva Attempts metric time series (attempts per minute) from local Athena data.

Purpose: build a per-minute Attempts series from CREATE events in the local Athena
``debug_states.csv``, plot it to PNG, and reconcile the totals against ``session.csv``
and the Lightstep smvod session counts.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/attempts/

Args:
    --tenant    Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date      Date to analyse (YYYY-MM-DD).
    --interval  Bucket size in whole minutes (default 1).

Assumption (to verify): one Attempt = one distinct sessionId with a PLAYER_SESSION_EVENT/CREATE
event, bucketed by the CREATE timestamp (UTC). Conviva's formula image is not readable from the docs.
"""
import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend must be set before pyplot import
import matplotlib.pyplot as plt  # noqa: E402

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


def plot(series: Counter, minutes: int, title: str, out: Path) -> None:
    step = timedelta(minutes=minutes)
    xs, t = [], min(series)
    while t <= max(series):
        xs.append(t)
        t += step
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(xs, [series.get(x, 0) for x in xs], linewidth=1)
    ax.set(title=title, xlabel="UTC time", ylabel=f"Attempts per {minutes} min")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--interval", type=int, default=1, help="bucket size in minutes")
    ap.add_argument("--out", type=Path, default=None)
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

    out = args.out or Path("tmp") / f"attempts_{args.tenant}_{args.date}.png"
    plot(series, args.interval, f"Attempts {args.tenant} {args.date} (CREATE events)", out)

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
