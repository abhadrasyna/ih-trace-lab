#!/usr/bin/env python3
"""Analyze a client-side "api-timing" probe export (xlsx, single sheet named
`in`), one row per CTAP/SM-VOD API call plus an optional paired traceroute
row for slow calls.

Columns (see `queries/exploration/api-timing.xlsx`):
record_type ('api'|'route'), <constant>, step (category/shared_content/
content_instance/playsession/manifest), content_id, category_id, title,
method, url, status_code, started_at, total_time_seconds,
dns_resolved_seconds, tcp_connected_seconds, tls_done_seconds,
request_sent_seconds, first_byte_seconds, response_complete_seconds,
redirect_time_seconds, size_download_bytes, speed_download_bytes_per_second,
x_amz_cf_pop, server_ip, route_status, route_output, route_error, error.

`record_type == 'route'` rows are a traceroute captured for that same call
(paired by content_id/step/started_at) and carry no dns/tcp/tls/ttfb
breakdown of their own - use `total_time_seconds` from the matching 'api'
row for that call's actual timing.

Usage:
    python3 scripts/analyze_api_timing.py summary <xlsx> [--sheet in]
        Per-step (category/shared_content/content_instance/playsession/
        manifest) n/min/median/p95/max/avg for total_time_seconds, api rows
        only.
    python3 scripts/analyze_api_timing.py breakdown <xlsx> [--sheet in]
        Per-step average phase breakdown (dns/tcp connect/tls/ttfb/download,
        ms), api rows only.
    python3 scripts/analyze_api_timing.py top <xlsx> [-n N] [--sheet in]
        Slowest N api rows by total_time_seconds, descending.
    python3 scripts/analyze_api_timing.py outliers <xlsx> --threshold-ms MS [--sheet in]
        All api rows at/above the given total_time threshold (ms).
    python3 scripts/analyze_api_timing.py routes <xlsx> [--sheet in]
        List every traceroute ('route' record_type) row: hop count, last
        responsive hop + latency, and whether the destination itself
        replied.
    python3 scripts/analyze_api_timing.py csv-summary <xlsx> --out <csv> [--sheet in]
        Write a per-step CSV summary (n, total_time min/median/p95/max/avg
        plus per-phase avg for dns/tcp_connect/tls/ttfb/download, all ms).
"""
import argparse
from lib import csv_io_compat as csv
import statistics

import openpyxl

NUMERIC_FIELDS = (
    "total_time_seconds",
    "dns_resolved_seconds",
    "tcp_connected_seconds",
    "tls_done_seconds",
    "request_sent_seconds",
    "first_byte_seconds",
    "response_complete_seconds",
    "redirect_time_seconds",
)


def load_rows(path, sheet="in"):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    header = [c.value for c in ws[1]]
    rows = []
    for raw in ws.iter_rows(min_row=2, values_only=True):
        r = dict(zip(header, raw))
        for f in NUMERIC_FIELDS:
            v = r.get(f)
            r[f] = float(v) if isinstance(v, (int, float)) else None
        rows.append(r)
    return rows


def api_rows(rows):
    return [r for r in rows if r.get("record_type") == "api"]


def percentile(values, pct):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def print_stats(label, values_s):
    """values_s: values in seconds; printed in ms."""
    values = [v * 1000.0 for v in values_s if v is not None]
    if not values:
        print(f"{label}: no data")
        return
    print(
        f"{label}: n={len(values)} min={min(values):.1f}ms "
        f"median={statistics.median(values):.1f}ms "
        f"p95={percentile(values, 95):.1f}ms "
        f"max={max(values):.1f}ms "
        f"avg={statistics.mean(values):.1f}ms"
    )


def cmd_summary(args):
    rows = api_rows(load_rows(args.xlsx, args.sheet))
    print(f"Total 'api' rows: {len(rows)}")
    steps = sorted({r.get("step") for r in rows if r.get("step")})
    for step in steps:
        step_rows = [r for r in rows if r.get("step") == step]
        print_stats(step, [r["total_time_seconds"] for r in step_rows])
    print_stats("ALL STEPS", [r["total_time_seconds"] for r in rows])


def phase_breakdown(r):
    """Return (dns, tcp_connect, tls, ttfb, download) phase durations in
    seconds, or None for any phase whose inputs are missing."""
    dns = r["dns_resolved_seconds"]
    tcp = r["tcp_connected_seconds"]
    tls = r["tls_done_seconds"]
    sent = r["request_sent_seconds"]
    first_byte = r["first_byte_seconds"]
    complete = r["response_complete_seconds"]
    tcp_connect = (tcp - dns) if (tcp is not None and dns is not None) else None
    tls_phase = (tls - tcp) if (tls is not None and tcp is not None) else None
    ttfb = (first_byte - sent) if (first_byte is not None and sent is not None) else None
    download = (complete - first_byte) if (complete is not None and first_byte is not None) else None
    return dns, tcp_connect, tls_phase, ttfb, download


def cmd_breakdown(args):
    rows = api_rows(load_rows(args.xlsx, args.sheet))
    steps = sorted({r.get("step") for r in rows if r.get("step")})
    for step in steps:
        step_rows = [r for r in rows if r.get("step") == step]
        phases = [phase_breakdown(r) for r in step_rows]
        print(f"--- {step} (n={len(step_rows)}) ---")
        for i, name in enumerate(("dns", "tcp_connect", "tls", "ttfb", "download")):
            print_stats(f"  {name}", [p[i] for p in phases])


def cmd_top(args):
    rows = api_rows(load_rows(args.xlsx, args.sheet))
    rows = [r for r in rows if r["total_time_seconds"] is not None]
    rows.sort(key=lambda r: r["total_time_seconds"], reverse=True)
    for r in rows[: args.n]:
        dns, tcp, tls, ttfb, dl = phase_breakdown(r)
        fmt = lambda v: f"{v * 1000:.1f}ms" if v is not None else "n/a"
        print(
            f"{r['total_time_seconds'] * 1000:8.1f}ms  step={r['step']:<16} "
            f"status={r['status_code']}  pop={r['x_amz_cf_pop']}  "
            f"dns={fmt(dns)} tcp={fmt(tcp)} tls={fmt(tls)} ttfb={fmt(ttfb)} dl={fmt(dl)}  "
            f"title={r.get('title')}  content_id={r.get('content_id')}  started_at={r.get('started_at')}"
        )


def cmd_outliers(args):
    rows = api_rows(load_rows(args.xlsx, args.sheet))
    threshold_s = args.threshold_ms / 1000.0
    rows = [r for r in rows if r["total_time_seconds"] is not None and r["total_time_seconds"] >= threshold_s]
    rows.sort(key=lambda r: r["total_time_seconds"], reverse=True)
    print(f"{len(rows)} api rows >= {args.threshold_ms}ms")
    for r in rows:
        dns, tcp, tls, ttfb, dl = phase_breakdown(r)
        fmt = lambda v: f"{v * 1000:.1f}ms" if v is not None else "n/a"
        print(
            f"{r['total_time_seconds'] * 1000:8.1f}ms  step={r['step']:<16} "
            f"status={r['status_code']}  pop={r['x_amz_cf_pop']}  server_ip={r['server_ip']}  "
            f"dns={fmt(dns)} tcp={fmt(tcp)} tls={fmt(tls)} ttfb={fmt(ttfb)} dl={fmt(dl)}  "
            f"content_id={r.get('content_id')}  started_at={r.get('started_at')}"
        )


def cmd_routes(args):
    rows = [r for r in load_rows(args.xlsx, args.sheet) if r.get("record_type") == "route"]
    print(f"{len(rows)} traceroute rows")
    for r in rows:
        output = r.get("route_output") or ""
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]
        responsive = [ln for ln in lines if "*" not in ln]
        last_responsive = responsive[-1].strip() if responsive else "none"
        print(
            f"step={r['step']:<16} status={r['status_code']}  pop={r['x_amz_cf_pop']}  "
            f"server_ip={r['server_ip']}  hops_total={len(lines)}  hops_responsive={len(responsive)}  "
            f"last_responsive_hop=[{last_responsive}]  content_id={r.get('content_id')}  "
            f"started_at={r.get('started_at')}"
        )


def _stat_row(values_s):
    values = [v * 1000.0 for v in values_s if v is not None]
    if not values:
        return {"n": 0, "min_ms": "", "median_ms": "", "p95_ms": "", "max_ms": "", "avg_ms": ""}
    return {
        "n": len(values),
        "min_ms": round(min(values), 1),
        "median_ms": round(statistics.median(values), 1),
        "p95_ms": round(percentile(values, 95), 1),
        "max_ms": round(max(values), 1),
        "avg_ms": round(statistics.mean(values), 1),
    }


def cmd_csv_summary(args):
    rows = api_rows(load_rows(args.xlsx, args.sheet))
    steps = sorted({r.get("step") for r in rows if r.get("step")})
    fieldnames = [
        "step",
        "n",
        "total_time_min_ms",
        "total_time_median_ms",
        "total_time_p95_ms",
        "total_time_max_ms",
        "total_time_avg_ms",
        "dns_avg_ms",
        "tcp_connect_avg_ms",
        "tls_avg_ms",
        "ttfb_avg_ms",
        "download_avg_ms",
    ]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for step in steps:
            step_rows = [r for r in rows if r.get("step") == step]
            total = _stat_row([r["total_time_seconds"] for r in step_rows])
            phases = [phase_breakdown(r) for r in step_rows]
            phase_avgs = []
            for i in range(5):
                vals = [p[i] * 1000.0 for p in phases if p[i] is not None]
                phase_avgs.append(round(statistics.mean(vals), 1) if vals else "")
            writer.writerow(
                {
                    "step": step,
                    "n": total["n"],
                    "total_time_min_ms": total["min_ms"],
                    "total_time_median_ms": total["median_ms"],
                    "total_time_p95_ms": total["p95_ms"],
                    "total_time_max_ms": total["max_ms"],
                    "total_time_avg_ms": total["avg_ms"],
                    "dns_avg_ms": phase_avgs[0],
                    "tcp_connect_avg_ms": phase_avgs[1],
                    "tls_avg_ms": phase_avgs[2],
                    "ttfb_avg_ms": phase_avgs[3],
                    "download_avg_ms": phase_avgs[4],
                }
            )
    print(f"Wrote {args.out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="Per-step total_time_seconds stats")
    p_summary.add_argument("xlsx")
    p_summary.add_argument("--sheet", default="in")
    p_summary.set_defaults(func=cmd_summary)

    p_breakdown = sub.add_parser("breakdown", help="Per-step dns/tcp/tls/ttfb/download phase averages")
    p_breakdown.add_argument("xlsx")
    p_breakdown.add_argument("--sheet", default="in")
    p_breakdown.set_defaults(func=cmd_breakdown)

    p_top = sub.add_parser("top", help="Slowest N api rows by total_time_seconds")
    p_top.add_argument("xlsx")
    p_top.add_argument("-n", type=int, default=10)
    p_top.add_argument("--sheet", default="in")
    p_top.set_defaults(func=cmd_top)

    p_outliers = sub.add_parser("outliers", help="All api rows at/above a total_time threshold")
    p_outliers.add_argument("xlsx")
    p_outliers.add_argument("--threshold-ms", type=float, required=True)
    p_outliers.add_argument("--sheet", default="in")
    p_outliers.set_defaults(func=cmd_outliers)

    p_routes = sub.add_parser("routes", help="List traceroute rows with hop/latency summary")
    p_routes.add_argument("xlsx")
    p_routes.add_argument("--sheet", default="in")
    p_routes.set_defaults(func=cmd_routes)

    p_csv = sub.add_parser("csv-summary", help="Write a per-step summary CSV")
    p_csv.add_argument("xlsx")
    p_csv.add_argument("--out", required=True)
    p_csv.add_argument("--sheet", default="in")
    p_csv.set_defaults(func=cmd_csv_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
