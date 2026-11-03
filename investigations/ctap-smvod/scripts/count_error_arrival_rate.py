#!/usr/bin/env python3
"""Daily arrival rate of one error code: sessions and unique households impacted, all tenants combined.

Reads `output/<TENANT>/daily/<YYYY-MM>_shaka-error-session.csv` (sessions) and `..._shaka-error-hhid.csv`
(unique households per day) from the repo-root output dir, takes the `--code` column, and sums per `session_date`
across tenants (household ids are tenant-scoped, so per-day sums do not double count). Prints per-day combined
and per-tenant tables, then mean/min/max per day. The mean drops the first day unless `--from` is given and the last day unless
`--to` is given (partial days; `--include-partial` keeps both). Fails on duplicate dates, missing days, or tenants
with different/short coverage. Reads existing files only -- never fires Athena/Lightstep.

Usage:
    python3 count_error_arrival_rate.py --code 6007
    python3 count_error_arrival_rate.py --code 6007 --from 2026-10-01 --to 2026-10-31 --tenants GH,ZA,ZM
"""
import argparse
import csv as std_csv
from datetime import date
from pathlib import Path

from lib.bootstrap import REPO_ROOT
from src.lib.logging.bootstrap import init_logging

OUTPUT_DIR = REPO_ROOT / "output"
METRICS = {"sessions": "shaka-error-session", "households": "shaka-error-hhid"}

DailyCounts = dict[date, int]


def read_code_column(path: Path, code: str) -> DailyCounts:
    """Pure-ish: {session_date: count} for one monthly daily file; fails if the code column is absent."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = std_csv.DictReader(fh)
        fields = reader.fieldnames or []
        if "session_date" not in fields or code not in fields:
            raise ValueError(f"{path}: needs columns session_date and {code!r}, has {fields}")
        counts: DailyCounts = {}
        for r in reader:
            d = date.fromisoformat(r["session_date"])
            if d in counts:
                raise ValueError(f"{path}: duplicate session_date {d}")
            if r[code] is None:
                raise ValueError(f"{path}: short row for {d}")
            counts[d] = int(r[code] or 0)
        return counts


def load_tenant(tenant_dir: Path, artifact: str, code: str) -> DailyCounts:
    files = sorted((tenant_dir / "daily").glob(f"*_{artifact}.csv"))
    if not files:
        raise FileNotFoundError(f"{tenant_dir}/daily/*_{artifact}.csv")
    counts: DailyCounts = {}
    for path in files:
        month = read_code_column(path, code)
        overlap = counts.keys() & month.keys()
        if overlap:
            raise ValueError(f"{path}: dates already seen in another file, e.g. {min(overlap)}")
        counts.update(month)
    return counts


def in_range(counts: DailyCounts, start: date | None, end: date | None) -> DailyCounts:
    return {d: n for d, n in counts.items() if (start is None or d >= start) and (end is None or d <= end)}


def check_aligned(per_tenant: dict[str, DailyCounts], start: date | None, end: date | None) -> None:
    """Every tenant must have the same contiguous days (and cover --from/--to), else zero vs no data is unknowable."""
    for tenant, counts in per_tenant.items():
        days = sorted(counts)
        if not days:
            raise ValueError(f"{tenant}: no days in range")
        if (days[-1] - days[0]).days + 1 != len(days):
            raise ValueError(f"{tenant}: missing days between {days[0]} and {days[-1]}")
        if (start and days[0] > start) or (end and days[-1] < end):
            raise ValueError(f"{tenant}: data {days[0]}..{days[-1]} does not cover requested {start}..{end}")
    spans = {(min(c), max(c)) for c in per_tenant.values()}
    if len(spans) > 1:
        raise ValueError(f"tenants cover different date ranges: { {t: (min(c), max(c)) for t, c in per_tenant.items()} }")


def combine(per_tenant: dict[str, DailyCounts]) -> DailyCounts:
    """Sum per-day counts across tenants."""
    total: DailyCounts = {}
    for counts in per_tenant.values():
        for d, n in counts.items():
            total[d] = total.get(d, 0) + n
    return total


def stats(daily: DailyCounts, drop_first: bool, drop_last: bool) -> dict[str, float]:
    """Mean/min/max per day, optionally dropping the first/last day (assumed partial)."""
    days = sorted(daily)[int(drop_first):len(daily) - int(drop_last)]
    if not days:
        raise ValueError("no days left to compute statistics over; use --include-partial")
    vals = [daily[d] for d in days]
    return {"days": len(vals), "mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}


def render(per_tenant: dict[str, dict[str, DailyCounts]], drop_first: bool, drop_last: bool) -> str:
    tenants = sorted(next(iter(per_tenant.values())))
    combined = {m: combine(per_tenant[m]) for m in per_tenant}
    days = sorted(set().union(*(set(c) for c in combined.values())))
    lines = ["date | sessions | households | " + " | ".join(f"{t} s/h" for t in tenants)]
    for d in days:
        split = " | ".join(f"{per_tenant['sessions'][t].get(d, 0)}/{per_tenant['households'][t].get(d, 0)}" for t in tenants)
        lines.append(f"{d} | {combined['sessions'].get(d, 0)} | {combined['households'].get(d, 0)} | {split}")
    for metric, daily in combined.items():
        s = stats(daily, drop_first, drop_last)
        unit = "session-days" if metric == "sessions" else "household-days (not distinct households)"
        lines.append(f"{metric}: mean {s['mean']:.1f}/day over {s['days']} days, min {s['min']}, max {s['max']}, "
                     f"sum of daily counts {sum(daily.values())} {unit}")
    return "\n".join(lines)


def main() -> None:
    init_logging("ctap-smvod-count_error_arrival_rate")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--code", required=True, help="Error code column, e.g. 6007")
    ap.add_argument("--from", dest="start", type=date.fromisoformat)
    ap.add_argument("--to", dest="end", type=date.fromisoformat)
    ap.add_argument("--tenants", help="Comma-separated tenants; default = every output/<T> with a daily/ folder")
    ap.add_argument("--include-partial", action="store_true",
                    help="Keep the first/last day in the mean (a given --from/--to already keeps that end)")
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()
    tenants = ([t.strip() for t in args.tenants.split(",") if t.strip()] if args.tenants
               else sorted(p.name for p in args.output_dir.iterdir() if (p / "daily").is_dir()))
    per_tenant = {m: {t: in_range(load_tenant(args.output_dir / t, art, args.code), args.start, args.end)
                      for t in tenants} for m, art in METRICS.items()}
    check_aligned({f"{m}/{t}": c for m, tc in per_tenant.items() for t, c in tc.items()}, args.start, args.end)
    keep = args.include_partial
    print(render(per_tenant, drop_first=not (keep or args.start), drop_last=not (keep or args.end)))


if __name__ == "__main__":
    main()
