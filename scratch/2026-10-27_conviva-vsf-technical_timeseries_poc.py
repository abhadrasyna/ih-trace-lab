"""POC: Conviva Video Start Failures Technical (VSF-T) time series from local Athena debug events.

Purpose: count sessions that failed to start because of a player error, bucket them by the failure
time, split business from technical errors by a configurable code list (default: none, so everything
is technical), and plot VSF-T plus its share of Attempts.

Conviva reference: https://docs.conviva.ai/sei/video/metric-dictionary/video-start-failures-technical/

Args:
    --tenant          Tenant identifier (resolve via scripts/resolve_tenant.py first).
    --date            Date to analyse (YYYY-MM-DD).
    --interval        Bucket size in whole minutes (default 5).
    --business-codes  Comma-separated error codes that are business errors (VSF-B); default none.
    --out-dir         Chart root (default output); PNG lands in <out-dir>/<tenant>/charts/.
    --report-dir      Markdown output (default docs/plan/conviva-metrics-recreation/vsf-technical).
    --top             Rows in the top tables (default 10).

Assumptions (to verify): Attempt = distinct sessionId with a CREATE event on the date (as the attempts POC).
VSF = attempt with a PLAYER_ERROR before any PLAYING state and before its DESTROY; a late error after
DESTROY is not a VSF. The failure time is the first such error (UTC). A session is VSF-B if any of its
pre-start errors is a business code, else VSF-T. Conviva's formula images are not readable from the docs.
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.line_chart import render_line  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "investigations/ctap-smvod/data"
TS = "%Y-%m-%dT%H:%M:%S.%fZ"


def read_sessions(path: Path) -> dict[str, list[tuple[datetime, str, str, str]]]:
    """sessionId -> time-sorted (ts, eventid, state, errorcode)."""
    out: dict[str, list] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["sessionId"]:
                out[r["sessionId"]].append((datetime.strptime(r["datetime"], TS), r["eventid"], r["state"], r["errorcode"]))
    for ev in out.values():
        ev.sort(key=lambda e: (e[0], e[1] != "PLAYER_ERROR"))  # on equal timestamps an error sorts before PLAYING
    return out


def create_time(events: list) -> datetime | None:
    return next((e[0] for e in events if e[1] == "PLAYER_SESSION_EVENT" and e[2] == "CREATE"), None)


def start_failure(events: list) -> tuple[datetime, list[str]] | None:
    """(first error time, error codes before start) if the session errored before PLAYING and DESTROY."""
    codes, first = [], None
    for ts, eid, state, code in events:
        if state == "PLAYING" or (eid == "PLAYER_SESSION_EVENT" and state == "DESTROY"):
            break
        if eid == "PLAYER_ERROR":
            first = first or ts
            codes.append(code or "(blank)")
    return (first, codes) if first else None


def bucket(times: list[datetime], minutes: int) -> Counter:
    step = timedelta(minutes=minutes)
    return Counter(datetime.min + ((t - datetime.min) // step) * step for t in times)


def series_points(series: Counter, minutes: int) -> tuple[list[datetime], list[int]]:
    step = timedelta(minutes=minutes)
    xs, t = [], min(series)
    while t <= max(series):
        xs.append(t)
        t += step
    return xs, [series.get(x, 0) for x in xs]


def read_content_by_session(path: Path) -> dict[str, tuple[str, str]]:
    """sessionId -> (content title, householdId) from the Athena session.csv."""
    out: dict[str, tuple[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            sid, title = r["sessionId"].strip(), r["content"].strip()
            if sid not in out or (title and not out[sid][0]):
                out[sid] = (title, r["householdId"].strip())
    return out


def top_content(ids: set[str], content: dict[str, tuple[str, str]], top: int) -> tuple[list[tuple[str, int, int]], int]:
    sessions: Counter = Counter()
    households: dict[str, set[str]] = {}
    for sid in ids:
        title, hh = content.get(sid, ("", ""))
        if title:
            sessions[title] += 1
            if hh:
                households.setdefault(title, set()).add(hh)
    rows = [(t, n, len(households.get(t, ()))) for t, n in sorted(sessions.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]
    return rows, len(ids) - sum(sessions.values())


def playback_type(sid: str) -> str:
    return "VOD" if sid.startswith("abr-vod-") else "Linear" if sid.startswith("abr-live-") else "Unresolved"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows] + [""]


def render_report(a: dict) -> str:
    n, tot = a["vsft"], a["attempts"]
    lines = [
        f"# Video Start Failures Technical — {a['tenant']}, {a['day']}", "",
        "VSF-T counts sessions that failed to start because of a technical player error "
        "([Conviva](https://docs.conviva.ai/sei/video/metric-dictionary/video-start-failures-technical/)). "
        f"Here: a session with a player error before playing, counted at the first error, UTC, {a['interval']}-minute buckets. "
        f"Business codes: {a['business'] or 'none configured, so all VSF is technical'}.", "",
        f"![VSF-T]({a['chart_rel']})", "",
        "## Headline", "",
        f"- VSF-T: **{n:,}** of {tot:,} attempts (**{n / tot:.1%}**); VSF-B: {a['vsfb']:,}",
        f"- Peak {a['interval']}-minute bucket: {a['peak'][1]:,} at {a['peak'][0]:%H:%M} UTC", "",
        "## Error codes", "",
        "A session can carry several codes, so rows do not add up to VSF-T.", "",
    ]
    lines += table(["Code", "VSF-T sessions", "% of VSF-T"], [[c, f"{k:,}", f"{k / n:.1%}"] for c, k in a["codes"]])
    lines += [f"## Top {len(a['rows'])} content by VSF-T", ""]
    lines += table(["#", "Content", "VSF-T", "% of VSF-T", "Households"],
                   [[str(i), t.replace("|", "/"), f"{k:,}", f"{k / n:.1%}", f"{h:,}"] for i, (t, k, h) in enumerate(a["rows"], 1)]
                   + [["", "Not resolved (no title)", f"{a['unresolved']:,}", f"{a['unresolved'] / n:.1%}", ""]])
    lines += ["## Playback type", ""]
    lines += table(["Type", "VSF-T", "% of VSF-T"], [[t, f"{k:,}", f"{k / n:.1%}"] for t, k in a["ptypes"]])
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--business-codes", default="", help="comma-separated business error codes")
    ap.add_argument("--out-dir", type=Path, default=Path("output"))
    ap.add_argument("--report-dir", type=Path, default=Path("docs/plan/conviva-metrics-recreation/vsf-technical"))
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    if args.interval < 1 or args.top < 1:
        ap.error("--interval and --top must be >= 1")
    business = {c.strip() for c in args.business_codes.split(",") if c.strip()}

    athena = DATA / "athena" / args.tenant
    sessions = read_sessions(athena / f"{args.date}_debug_all_events.csv")
    attempts = {s for s, ev in sessions.items() if (t := create_time(ev)) and t.date().isoformat() == args.date}
    if not attempts:
        raise SystemExit(f"no CREATE events for {args.tenant} on {args.date}")

    failures = {s: f for s in attempts if (f := start_failure(sessions[s]))}
    tech = {s: f for s, f in failures.items() if not business & set(f[1])}
    if not tech:
        raise SystemExit("no VSF-T sessions found")
    series = bucket([f[0] for f in tech.values()], args.interval)
    xs, ys = series_points(series, args.interval)
    n, tot = len(tech), len(attempts)

    png = render_line(
        xs, ys,
        title=f"Video Start Failures Technical — {args.tenant}, {args.date}",
        kpi=("VSF-T (sum of points)", f"{n:,}  ({n / tot:.1%} of attempts)"),
        footer=f"Per {args.interval} min, UTC, at first error. Base: Athena debug events; business codes: {','.join(sorted(business)) or 'none'}.",
    )
    out = write_chart_png(png, args.out_dir, args.tenant, f"{args.date}_vsf-technical_{args.interval}min.png")

    code_counts = Counter(c for _, codes in tech.values() for c in set(codes))
    rows, unresolved = top_content(set(tech), read_content_by_session(athena / f"{args.date}_session.csv"), args.top)
    report = args.report_dir / f"{args.date}_{args.tenant}_vsf-technical-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    analysis = {
        "tenant": args.tenant, "day": args.date, "interval": args.interval, "business": ", ".join(sorted(business)),
        "vsft": n, "attempts": tot, "vsfb": len(failures) - n,
        "peak": min(series.items(), key=lambda kv: (-kv[1], kv[0])),
        "chart_rel": Path(os.path.relpath(out, report.parent)).as_posix(),
        "codes": code_counts.most_common(args.top), "rows": rows, "unresolved": unresolved,
        "ptypes": Counter(playback_type(s) for s in tech).most_common(),
    }
    report.write_text(render_report(analysis), encoding="utf-8")

    with (athena / f"{args.date}_outcome_first_debug.csv").open(newline="", encoding="utf-8-sig") as fh:
        outcome = {r["sessionId"]: r["outcome"] for r in csv.DictReader(fh)}
    vsf_ref = {s for s, o in outcome.items() if o == "VSF"}
    print(f"chart: {out}\nreport: {report}")
    print(f"attempts={tot} VSF={len(failures)} VSF-T={n} VSF-B={len(failures) - n} ({n / tot:.2%})")
    print(f"outcome_first_debug VSF={len(vsf_ref)} overlap={len(vsf_ref & set(tech))} only-here={len(set(tech) - vsf_ref)} only-there={len(vsf_ref - set(tech))}")

if __name__ == "__main__":
    main()
