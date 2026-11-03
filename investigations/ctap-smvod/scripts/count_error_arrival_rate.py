#!/usr/bin/env python3
"""Daily arrival rate per error code: sessions and unique households impacted, all tenants combined.

Reads `output/<TENANT>/daily/<YYYY-MM>_shaka-error-session.csv` (sessions) and `..._shaka-error-hhid.csv`
(unique households per day) from the repo-root output dir and sums per `session_date` across tenants (household ids
are tenant-scoped, so per-day sums do not double count). A code a tenant/file has no column for counts as 0.

`--codes` takes a comma list (e.g. 6007,1003), `all` (every code column found) or `families` (default: only
1xxx, 3xxx and 6xxx codes). The summary table is grouped by family with mean/min/max per day for each code; the
family row is the sum of its codes (a session with several codes counts once per code). `--detail` prints the
per-day tables (implied for a single code) and a code-by-day matrix is always written to
`output/error_code/arrival_rate_<first>_<last>.csv` (long format: date, code, sessions, households).

The mean drops the first day unless `--from` is given and the last day unless `--to` is given (partial days;
`--include-partial` keeps both). Fails on duplicate dates, missing days, short rows or tenants with different/short
coverage. Reads existing files only -- never fires Athena/Lightstep.

Usage:
    python3 count_error_arrival_rate.py                       # 1xxx/3xxx/6xxx families, all tenants
    python3 count_error_arrival_rate.py --codes 6007,1003 --from 2026-10-01 --to 2026-10-31 --tenants GH,ZA,ZM
    python3 count_error_arrival_rate.py --code 6007           # single code, per-day detail
    python3 count_error_arrival_rate.py --codes all --chart   # + output/error_code/charts/arrival_rate_*_sessions.png

`--chart` draws one line per code per day; with many codes (`all`) only the `--chart-top` (default 8) codes by total get
their own line and the rest are summed into one muted "other (N codes)" line. `--chart-metric households` plots households.
"""
import argparse
import csv as std_csv
import re
from datetime import date
from pathlib import Path

from lib.arrival_rate_chart import DEFAULT_TOP, render_arrival_chart
from lib.bootstrap import REPO_ROOT
from src.lib.charts.output import write_chart_png
from src.lib.logging.bootstrap import init_logging

OUTPUT_DIR = REPO_ROOT / "output"
METRICS = {"sessions": "shaka-error-session", "households": "shaka-error-hhid"}
FAMILIES = ("1xxx", "3xxx", "6xxx")
OTHER = "other"

DailyCounts = dict[date, int]
CodeCounts = dict[str, DailyCounts]  # code -> day -> count


def family_of(code: str) -> str:
    """'6007' -> '6xxx'; anything not a 4-digit code -> 'other'."""
    return f"{code[0]}xxx" if re.fullmatch(r"\d{4}", code) else OTHER


def read_daily_file(path: Path) -> CodeCounts:
    """{code: {session_date: count}} for every code column of one daily file; fails on bad rows."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = std_csv.DictReader(fh)
        fields = reader.fieldnames or []
        if "session_date" not in fields:
            raise ValueError(f"{path}: needs a session_date column, has {fields}")
        codes = [f for f in fields if f != "session_date"]
        out: CodeCounts = {c: {} for c in codes}
        seen: set[date] = set()
        for r in reader:
            d = date.fromisoformat(r["session_date"])
            if d in seen:
                raise ValueError(f"{path}: duplicate session_date {d}")
            seen.add(d)
            for c in codes:
                if r[c] is None:
                    raise ValueError(f"{path}: short row for {d}")
                out[c][d] = int(r[c] or 0)
        return out


def load_tenant(tenant_dir: Path, artifact: str) -> CodeCounts:
    """Merge a tenant's monthly files; a code missing from a file is 0 for that file's days."""
    files = sorted((tenant_dir / "daily").glob(f"*_{artifact}.csv"))
    if not files:
        raise FileNotFoundError(f"{tenant_dir}/daily/*_{artifact}.csv")
    parsed = [(path, read_daily_file(path)) for path in files]
    all_codes = {c for _, data in parsed for c in data}
    merged: CodeCounts = {c: {} for c in all_codes}
    seen: set[date] = set()
    for path, data in parsed:
        days = {d for counts in data.values() for d in counts}
        overlap = seen & days
        if overlap:
            raise ValueError(f"{path}: dates already seen in another file, e.g. {min(overlap)}")
        seen |= days
        for c in all_codes:
            merged[c].update(data.get(c) or {d: 0 for d in days})
    return merged


def in_range(data: CodeCounts, start: date | None, end: date | None) -> CodeCounts:
    return {c: {d: n for d, n in counts.items() if (start is None or d >= start) and (end is None or d <= end)}
            for c, counts in data.items()}


def tenant_days(data: CodeCounts) -> DailyCounts:
    """Day set of a tenant (every code carries all days)."""
    if not data:
        raise ValueError("tenant has no code columns")
    return next(iter(data.values()))


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


def select_codes(available: set[str], spec: str) -> list[str]:
    """Resolve --codes: comma list (must exist), 'all', or 'families' (1xxx/3xxx/6xxx). Sorted."""
    if spec == "all":
        return sorted(available)
    if spec == "families":
        return sorted(c for c in available if family_of(c) in FAMILIES)
    wanted = [c.strip() for c in spec.split(",") if c.strip()]
    unknown = sorted(set(wanted) - available)
    if unknown:
        raise ValueError(f"codes not found in any file: {unknown}; available: {sorted(available)}")
    return sorted(set(wanted))


def stats(daily: DailyCounts, drop_first: bool, drop_last: bool) -> dict[str, float]:
    """Mean/min/max per day, optionally dropping the first/last day (assumed partial)."""
    days = sorted(daily)[int(drop_first):len(daily) - int(drop_last)]
    if not days:
        raise ValueError("no days left to compute statistics over; use --include-partial")
    vals = [daily[d] for d in days]
    return {"days": len(vals), "mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals),
            "sum": sum(daily.values())}


def combined_by_code(per_metric: dict[str, dict[str, CodeCounts]], codes: list[str]) -> dict[str, dict[str, DailyCounts]]:
    """metric -> code -> combined-over-tenants daily counts (0 where a tenant lacks the code)."""
    out: dict[str, dict[str, DailyCounts]] = {}
    for metric, tenants in per_metric.items():
        out[metric] = {c: combine({t: data.get(c) or {d: 0 for d in tenant_days(data)} for t, data in tenants.items()})
                       for c in codes}
    return out


def summary_table(combined: dict[str, dict[str, DailyCounts]], codes: list[str], drop_first: bool, drop_last: bool) -> str:
    """Per-family table: one row per code, family row = sum of its codes (per day, then stats)."""
    header = "code | sessions mean/min/max per day | households mean/min/max per day | sessions sum"
    groups: dict[str, list[str]] = {}
    for c in codes:
        groups.setdefault(family_of(c), []).append(c)
    order = [f for f in (*FAMILIES, OTHER) if f in groups] + sorted(set(groups) - {*FAMILIES, OTHER})
    lines = [header]
    for fam in order:
        rows = []
        for label, members in [(c, [c]) for c in groups[fam]] + ([(f"{fam} (sum of codes)", groups[fam])] if len(groups[fam]) > 1 else []):
            cells = []
            for metric in METRICS:
                daily = combine({c: combined[metric][c] for c in members})
                s = stats(daily, drop_first, drop_last)
                cells.append((s, f"{s['mean']:.1f}/{s['min']}/{s['max']}"))
            rows.append(f"{label} | {cells[0][1]} | {cells[1][1]} | {cells[0][0]['sum']}")
        lines.append(f"-- {fam} --")
        lines.extend(rows)
    return "\n".join(lines)


def detail_table(per_metric: dict[str, dict[str, CodeCounts]], combined: dict[str, dict[str, DailyCounts]], code: str) -> str:
    """Per-day combined and per-tenant (sessions/households) rows for one code."""
    tenants = sorted(per_metric["sessions"])
    days = sorted(combined["sessions"][code])
    lines = [f"[{code}] date | sessions | households | " + " | ".join(f"{t} s/h" for t in tenants)]
    for d in days:
        split = " | ".join(
            f"{(per_metric['sessions'][t].get(code) or {}).get(d, 0)}/{(per_metric['households'][t].get(code) or {}).get(d, 0)}"
            for t in tenants)
        lines.append(f"{d} | {combined['sessions'][code][d]} | {combined['households'][code][d]} | {split}")
    return "\n".join(lines)


def matrix_rows(combined: dict[str, dict[str, DailyCounts]], codes: list[str]) -> list[list[str | int]]:
    """Long-format rows [date, code, sessions, households] for the CSV."""
    return [[d, c, combined["sessions"][c][d], combined["households"][c][d]]
            for c in codes for d in sorted(combined["sessions"][c])]


def write_matrix(path: Path, rows: list[list[str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = std_csv.writer(fh)
        w.writerow(["date", "code", "sessions", "households"])
        w.writerows(rows)


def main() -> None:
    init_logging("ctap-smvod-count_error_arrival_rate")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--codes", "--code", dest="codes", default="families",
                    help="Comma list (6007,1003), 'all', or 'families' (1xxx/3xxx/6xxx; default)")
    ap.add_argument("--from", dest="start", type=date.fromisoformat)
    ap.add_argument("--to", dest="end", type=date.fromisoformat)
    ap.add_argument("--tenants", help="Comma-separated tenants; default = every output/<T> with a daily/ folder")
    ap.add_argument("--include-partial", action="store_true",
                    help="Keep the first/last day in the mean (a given --from/--to already keeps that end)")
    ap.add_argument("--detail", action="store_true", help="Also print per-day tables per code (implied for one code)")
    ap.add_argument("--chart", action="store_true",
                    help="Also write a day-wise line chart to output/error_code/charts/")
    ap.add_argument("--chart-metric", choices=list(METRICS), default="sessions")
    ap.add_argument("--chart-top", type=int, choices=range(1, DEFAULT_TOP + 1), metavar=f"1..{DEFAULT_TOP}",
                    default=DEFAULT_TOP,
                    help="Codes drawn as their own line, ranked by total; the rest are summed into 'other'")
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()
    tenants = ([t.strip() for t in args.tenants.split(",") if t.strip()] if args.tenants
               else sorted(p.name for p in args.output_dir.iterdir() if (p / "daily").is_dir()))
    per_metric = {m: {t: in_range(load_tenant(args.output_dir / t, art), args.start, args.end) for t in tenants}
                  for m, art in METRICS.items()}
    check_aligned({f"{m}/{t}": tenant_days(data) for m, tc in per_metric.items() for t, data in tc.items()},
                  args.start, args.end)
    available = {c for tc in per_metric.values() for data in tc.values() for c in data}
    codes = select_codes(available, args.codes)
    if not codes:
        raise ValueError(f"no codes matched --codes {args.codes!r}")
    combined = combined_by_code(per_metric, codes)
    keep = args.include_partial
    drop_first, drop_last = not (keep or args.start), not (keep or args.end)
    if args.detail or len(codes) == 1:
        print("\n\n".join(detail_table(per_metric, combined, c) for c in codes) + "\n")
    print(summary_table(combined, codes, drop_first, drop_last))
    days = sorted(combined["sessions"][codes[0]])
    out = args.output_dir / "error_code" / f"arrival_rate_{days[0]}_{days[-1]}.csv"
    write_matrix(out, matrix_rows(combined, codes))
    print(f"\nmatrix -> {out}")
    if args.chart:
        name = f"arrival_rate_{days[0]}_{days[-1]}_{args.chart_metric}.png"
        png = render_arrival_chart(combined[args.chart_metric], args.chart_metric,
                                   f"Error arrival rate per code, {days[0]} to {days[-1]}", args.chart_top)
        print(f"chart -> {write_chart_png(png, args.output_dir, 'error_code', name)}")


if __name__ == "__main__":
    main()
