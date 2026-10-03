#!/usr/bin/env python3
"""Analyze a session-guard "Request vs. Upstream Time" Lightstep CSV export
(see the "session-guard Request vs. Upstream Time (by device)" template in
`applauseInvestigation/knowledge/lightstep-query-templates.md`).

These CSVs have one row per FCID (near-unique per request, since the query's
group_by includes `http.request_time`/`FCID`), with columns:
http.route, http.status_code, http.request_time, http.upstream_response_time,
FCID, min, max, avg, sum, value. `http.request_time`/`http.upstream_response_time`
are seconds (as strings). Net latency = request_time - upstream_response_time,
i.e. session-guard's own overhead on top of whatever it proxies to upstream.

Usage:
    python3 scripts/analyze_session_guard_net_latency.py summary <csv>
        Print row count and min/median/p95/max/avg for request_time,
        upstream_response_time, and net_latency (all in ms).
    python3 scripts/analyze_session_guard_net_latency.py top <csv> [-n N] [--by net_latency|request_time|upstream_response_time]
        Print the top N rows sorted by the chosen metric, descending.
    python3 scripts/analyze_session_guard_net_latency.py show <csv> <substring>
        Print every row whose http.route or FCID contains <substring>
        (case-insensitive).
    python3 scripts/analyze_session_guard_net_latency.py locate <csv> --ttfb-ms MS [--tolerance-ms MS]
        Find rows whose request_time (converted to ms) is within
        tolerance of a given HAR "Waiting for first byte" (TTFB) value -
        use this to identify which session-guard row corresponds to a
        HAR waterfall sample when no FCID is available.
"""
import argparse
from lib import csv_io_compat as csv
import statistics


def load_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        try:
            r["_request_ms"] = float(r["http.request_time"]) * 1000.0
        except (KeyError, ValueError, TypeError):
            r["_request_ms"] = None
        try:
            r["_upstream_ms"] = float(r["http.upstream_response_time"]) * 1000.0
        except (KeyError, ValueError, TypeError):
            r["_upstream_ms"] = None
        if r["_request_ms"] is not None and r["_upstream_ms"] is not None:
            r["_net_ms"] = r["_request_ms"] - r["_upstream_ms"]
        else:
            r["_net_ms"] = None
    return rows


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


def print_stats(label, values):
    values = [v for v in values if v is not None]
    if not values:
        print(f"{label}: no data")
        return
    print(
        f"{label}: n={len(values)} min={min(values):.2f}ms "
        f"median={statistics.median(values):.2f}ms "
        f"p95={percentile(values, 95):.2f}ms "
        f"max={max(values):.2f}ms "
        f"avg={statistics.mean(values):.2f}ms"
    )


def cmd_summary(args):
    rows = load_rows(args.csv)
    print(f"Total rows: {len(rows)}")
    print_stats("request_time", [r["_request_ms"] for r in rows])
    print_stats("upstream_response_time", [r["_upstream_ms"] for r in rows])
    print_stats("net_latency (request - upstream)", [r["_net_ms"] for r in rows])


def cmd_top(args):
    rows = load_rows(args.csv)
    key = f"_{args.by.replace('request_time', 'request').replace('upstream_response_time', 'upstream').replace('net_latency', 'net')}_ms"
    rows = [r for r in rows if r.get(key) is not None]
    rows.sort(key=lambda r: r[key], reverse=True)
    for r in rows[: args.n]:
        print(
            f"{r[key]:8.2f}ms  route={r['http.route']}  status={r['http.status_code']}  "
            f"request_time={r['_request_ms']:.2f}ms  upstream={r['_upstream_ms']:.2f}ms  "
            f"net={r['_net_ms']:.2f}ms  FCID={r['FCID']}"
        )


def cmd_show(args):
    rows = load_rows(args.csv)
    needle = args.substring.lower()
    for r in rows:
        if needle in r.get("http.route", "").lower() or needle in r.get("FCID", "").lower():
            print(
                f"route={r['http.route']}  status={r['http.status_code']}  "
                f"request_time={r['_request_ms']:.2f}ms  upstream={r['_upstream_ms']:.2f}ms  "
                f"net={r['_net_ms']:.2f}ms  FCID={r['FCID']}"
            )


def cmd_locate(args):
    rows = load_rows(args.csv)
    matches = [
        r
        for r in rows
        if r["_request_ms"] is not None and abs(r["_request_ms"] - args.ttfb_ms) <= args.tolerance_ms
    ]
    if not matches:
        print(f"No rows with request_time within {args.tolerance_ms}ms of {args.ttfb_ms}ms")
        return
    matches.sort(key=lambda r: abs(r["_request_ms"] - args.ttfb_ms))
    for r in matches:
        print(
            f"Δ={abs(r['_request_ms'] - args.ttfb_ms):.2f}ms  route={r['http.route']}  "
            f"status={r['http.status_code']}  request_time={r['_request_ms']:.2f}ms  "
            f"upstream={r['_upstream_ms']:.2f}ms  net={r['_net_ms']:.2f}ms  FCID={r['FCID']}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="Overall stats for request_time/upstream_response_time/net_latency")
    p_summary.add_argument("csv")
    p_summary.set_defaults(func=cmd_summary)

    p_top = sub.add_parser("top", help="Top N rows by a chosen metric")
    p_top.add_argument("csv")
    p_top.add_argument("-n", type=int, default=10)
    p_top.add_argument("--by", choices=["net_latency", "request_time", "upstream_response_time"], default="net_latency")
    p_top.set_defaults(func=cmd_top)

    p_show = sub.add_parser("show", help="Rows matching a route/FCID substring")
    p_show.add_argument("csv")
    p_show.add_argument("substring")
    p_show.set_defaults(func=cmd_show)

    p_locate = sub.add_parser("locate", help="Find rows near a given HAR TTFB value (ms)")
    p_locate.add_argument("csv")
    p_locate.add_argument("--ttfb-ms", type=float, required=True)
    p_locate.add_argument("--tolerance-ms", type=float, default=10.0)
    p_locate.set_defaults(func=cmd_locate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
