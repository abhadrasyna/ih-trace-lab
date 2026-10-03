#!/usr/bin/env python3
"""
Analyze a finished output/YYYY-MM-DD_setupsession_with_outcome.csv report and
print (or save) the recurring daily write-up: playback_outcome distribution,
buffering/startup stats + outliers, state_sequence pattern checks, device/
platform breakdowns, the "missing" root-cause investigation, and a
householdId anomaly scan.

This is read-only analysis over an already-built report -- it does not touch
merge_ctap_smvod_csv.py / merge_session_outcome.py or their inputs, and
writes nothing unless --out is given. Uses only the standard library (no
pandas dependency), consistent with the rest of scripts/.

See docs/STATUS.md, BLUEPRINT.md, LEGEND.md and queries/QUERY_CATALOG.md for
the meaning of each column and how this data is produced upstream.

Usage:
    python3 analyze_outcome_report.py --date 09072026
    python3 analyze_outcome_report.py --date 09072026 --out ../docs/09072026.md
    python3 analyze_outcome_report.py --date 09072026 \
        --report ../output/2026-07-09_setupsession_with_outcome.csv \
        --debug-states ../data/athena/2026-07-09_debug_states.csv
"""
import argparse
from lib import csv_io_compat as csv
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

from lib.runtime import investigation_output_dir, snapshot_output_path

SESSION_KEY = "sessionId"
OUTCOMES = ["DESTROY", "EBVS", "INCOMPLETE_NO_DESTROY", "PLAYER_ERROR", "missing"]

# Standard householdId shape: opaque ~52-char token, alnum/-/_ only.
HOUSEHOLD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{40,60}$")


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _date_ddmmyyyy_to_iso(raw_date):
    return datetime.strptime(raw_date, "%d%m%Y").strftime("%Y-%m-%d")


def to_float(v):
    try:
        if v in (None, ""):
            return None
        return float(v)
    except ValueError:
        return None


def outcome_of(row):
    return row.get("playback_outcome") or "missing"


def fmt_pct(n, total):
    return f"{100 * n / total:.1f}%" if total else "0.0%"


def section_outcome_distribution(rows):
    total = len(rows)
    counts = Counter(outcome_of(r) for r in rows)
    lines = ["## 1. `playback_outcome` distribution", "",
             "| Outcome | Count | % |", "|---|---|---|"]
    for outcome, count in counts.most_common():
        label = "missing (no `unified_sessions` row)" if outcome == "missing" else outcome
        lines.append(f"| {label} | {count} | {fmt_pct(count, total)} |")
    lines.append("")
    return "\n".join(lines), counts


def quantile(values, q):
    if not values:
        return None
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1] if 1 <= q <= 99 else None


def section_buffering(rows, top_n=5):
    counts = [to_float(r.get("buffering_count")) for r in rows]
    counts = [c for c in counts if c is not None]
    totals = [to_float(r.get("buffering_total_ms")) for r in rows]
    totals_present = [t for t in totals if t is not None]

    lines = ["## 2. Buffering stats", ""]
    if counts:
        lines.append(f"- `buffering_count`: mean {statistics.mean(counts):.2f}, "
                      f"median {statistics.median(counts):.0f}, max {max(counts):.0f} "
                      f"({len(counts)}/{len(rows)} sessions have data).")
    if totals_present:
        lines.append(f"- `buffering_total_ms`: mean ~{statistics.mean(totals_present):,.0f} ms, "
                      f"median {statistics.median(totals_present):,.0f} ms, "
                      f"max {max(totals_present):,.0f} ms.")
    lines.append("")

    ranked = sorted(
        (r for r in rows if to_float(r.get("buffering_total_ms"))),
        key=lambda r: to_float(r.get("buffering_total_ms")),
        reverse=True,
    )[:top_n]
    if ranked:
        lines.append(f"**Top {len(ranked)} by `buffering_total_ms` (flag for review):**")
        lines.append("")
        lines.append("| sessionId | playback_outcome | OS Family | Browser Name | buffering_count | buffering_total_ms | startup_time_ms |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in ranked:
            lines.append(f"| {r.get(SESSION_KEY, '')} | {outcome_of(r)} | {r.get('OS Family', '')} | "
                         f"{r.get('Browser Name', '')} | {r.get('buffering_count', '')} | "
                         f"{r.get('buffering_total_ms', '')} | {r.get('startup_time_ms', '')} |")
    lines.append("")
    return "\n".join(lines)


def section_startup(rows, top_n=5, slow_threshold_ms=15000):
    vals = [to_float(r.get("startup_time_ms")) for r in rows]
    vals_present = [v for v in vals if v is not None]

    lines = ["## 3. Startup time (`startup_time_ms`)", ""]
    if vals_present:
        p50 = quantile(vals_present, 50)
        p75 = quantile(vals_present, 75)
        p90 = quantile(vals_present, 90)
        p95 = quantile(vals_present, 95)
        lines.append(f"- Mean {statistics.mean(vals_present) / 1000:.1f}s, median {p50 / 1000:.1f}s, "
                      f"75th pct {p75 / 1000:.1f}s, 90th pct {p90 / 1000:.1f}s, "
                      f"95th pct {p95 / 1000:.1f}s, max {max(vals_present) / 1000:.1f}s "
                      f"({len(vals_present)}/{len(rows)} sessions have data).")
        slow = [v for v in vals_present if v > slow_threshold_ms]
        lines.append(f"- {len(slow)}/{len(vals_present)} sessions ({fmt_pct(len(slow), len(vals_present))}) "
                      f"exceed {slow_threshold_ms / 1000:.0f}s startup -- flag for review.")
    lines.append("")

    # Mean startup by OS Family / Browser Name -- flags broad platform-wide regressions.
    groups = defaultdict(list)
    for r in rows:
        v = to_float(r.get("startup_time_ms"))
        if v is not None:
            groups[(r.get("OS Family", ""), r.get("Browser Name", ""))].append(v)
    if groups:
        lines.append("**Mean startup by OS Family / Browser Name:**")
        lines.append("")
        lines.append("| OS Family | Browser Name | Mean (ms) | Median (ms) | Count |")
        lines.append("|---|---|---|---|---|")
        for (os_family, browser), vs in sorted(groups.items(), key=lambda kv: -statistics.mean(kv[1])):
            lines.append(f"| {os_family} | {browser} | {statistics.mean(vs):,.0f} | "
                         f"{statistics.median(vs):,.0f} | {len(vs)} |")
        lines.append("")

    ranked = sorted(
        (r for r in rows if to_float(r.get("startup_time_ms"))),
        key=lambda r: to_float(r.get("startup_time_ms")),
        reverse=True,
    )[:top_n]
    if ranked:
        lines.append(f"**Top {len(ranked)} slowest starts (flag for review):**")
        lines.append("")
        lines.append("| sessionId | playback_outcome | OS Family | Browser Name | startup_time_ms | error_codes |")
        lines.append("|---|---|---|---|---|---|")
        for r in ranked:
            lines.append(f"| {r.get(SESSION_KEY, '')} | {outcome_of(r)} | {r.get('OS Family', '')} | "
                         f"{r.get('Browser Name', '')} | {r.get('startup_time_ms', '')} | "
                         f"{r.get('error_codes', '')} |")
    lines.append("")
    return "\n".join(lines)


def _seq(row):
    return row.get("state_sequence") or ""


def section_state_sequence(rows):
    lines = ["## 4. `state_sequence` patterns", ""]
    with_seq = [r for r in rows if _seq(r)]
    lines.append(f"- {len(with_seq)}/{len(rows)} sessions have a `state_sequence`.")
    lines.append("")

    buf_no_play = [r for r in with_seq if "BUFFERING" in _seq(r) and "PLAYING" not in _seq(r)]
    lines.append(f"**BUFFERING with no PLAYING ({len(buf_no_play)} sessions):** "
                 f"outcome mix -- {dict(Counter(outcome_of(r) for r in buf_no_play))}")
    lines.append("")

    no_destroy = [r for r in with_seq if "DESTROY" not in _seq(r)]
    lines.append(f"**Has `state_sequence` but no DESTROY ({len(no_destroy)} sessions):** "
                 f"outcome mix -- {dict(Counter(outcome_of(r) for r in no_destroy))}")
    lines.append("")

    mismatch = [r for r in with_seq
                if outcome_of(r) == "INCOMPLETE_NO_DESTROY" and "DESTROY" in _seq(r)]
    lines.append(f"**Outcome/lifecycle mismatch -- `INCOMPLETE_NO_DESTROY` but `state_sequence` "
                 f"HAS DESTROY ({len(mismatch)} sessions):** likely a `unified_sessions` "
                 f"completeness gap rather than a genuinely ambiguous session -- see §7-style "
                 f"cross-check before trusting `playback_outcome` alone for these.")
    if mismatch:
        lines.append("")
        lines.append("| sessionId | OS Family | Browser Name | error_codes | startup_time_ms |")
        lines.append("|---|---|---|---|---|")
        for r in mismatch[:15]:
            lines.append(f"| {r.get(SESSION_KEY, '')} | {r.get('OS Family', '')} | "
                         f"{r.get('Browser Name', '')} | {r.get('error_codes', '')} | "
                         f"{r.get('startup_time_ms', '')} |")
        if len(mismatch) > 15:
            lines.append(f"| ... | {len(mismatch) - 15} more rows omitted | | | |")
    lines.append("")

    def repeated(seq, tok):
        return seq.count(tok) > 1

    flapping = [r for r in with_seq if repeated(_seq(r), "DESTROY") or repeated(_seq(r), "STOPPED")]
    lines.append(f"**Flapping -- repeated DESTROY or STOPPED ({len(flapping)} sessions):** "
                 f"duplicate lifecycle-event delivery signature.")
    lines.append("")

    def error_after_destroy(seq):
        if "ERROR" not in seq or "DESTROY" not in seq:
            return False
        return seq.rfind("ERROR") > seq.find("DESTROY")

    ooo = [r for r in with_seq if error_after_destroy(_seq(r))]
    lines.append(f"**ERROR after DESTROY/STOPPED -- out-of-order event ({len(ooo)} sessions):** "
                 f"a possible late/out-of-order event-delivery bug if recurring across days.")
    if ooo:
        lines.append("")
        lines.append("| sessionId | playback_outcome | state_sequence |")
        lines.append("|---|---|---|")
        for r in ooo:
            lines.append(f"| {r.get(SESSION_KEY, '')} | {outcome_of(r)} | {_seq(r)} |")
    lines.append("")

    def stopped_before_destroy(seq):
        i1, i2 = seq.find("STOPPED"), seq.find("DESTROY")
        return i1 != -1 and i2 != -1 and i1 < i2

    sbd = [r for r in with_seq if stopped_before_destroy(_seq(r))]
    lines.append(f"**STOPPED before DESTROY ordering:** {len(sbd)} sessions (normal/expected ordering).")
    lines.append("")
    return "\n".join(lines)


def section_device_browser(rows):
    lines = ["## 5. Device/Browser vs. Outcome", ""]

    for col in ["OS Family", "Browser Name", "Device Class"]:
        values = sorted({r.get(col, "") for r in rows if r.get(col)})
        lines.append(f"| {col} | " + " | ".join(OUTCOMES) + " | Total |")
        lines.append("|---|" + "---|" * (len(OUTCOMES) + 1))
        totals_by_outcome = Counter()
        for v in values:
            sub = [r for r in rows if r.get(col, "") == v]
            counts = Counter(outcome_of(r) for r in sub)
            row_cells = [str(counts.get(o, 0)) for o in OUTCOMES]
            lines.append(f"| {v} | " + " | ".join(row_cells) + f" | {len(sub)} |")
            for o in OUTCOMES:
                totals_by_outcome[o] += counts.get(o, 0)
        lines.append("")
    return "\n".join(lines)


def _classify_success(counts, total):
    destroy = counts.get("DESTROY", 0)
    if destroy == 0:
        return "\u274c Zero DESTROY -- no confirmed success"
    if destroy == total:
        return "\u2705 Confirmed success"
    pct = 100 * destroy / total if total else 0
    return f"\u26a0\ufe0f Mixed, {pct:.0f}% confirmed success"


def section_platform(rows):
    lines = ["## 6. Platform breakdown (raw User-Agent `Platform` column)", ""]
    by_platform = defaultdict(list)
    for r in rows:
        p = r.get("Platform") or "(blank / no UA platform token)"
        by_platform[p].append(r)

    header = ["Platform", "Count"] + OUTCOMES + ["Playback success?"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))

    total_counts = Counter()
    total_rows = 0
    zero_destroy_platforms = []
    for platform, sub in sorted(by_platform.items(), key=lambda kv: -len(kv[1])):
        counts = Counter(outcome_of(r) for r in sub)
        cells = [platform, str(len(sub))] + [str(counts.get(o, 0)) for o in OUTCOMES]
        success = _classify_success(counts, len(sub))
        cells.append(success)
        lines.append("| " + " | ".join(cells) + " |")
        total_counts.update(counts)
        total_rows += len(sub)
        if counts.get("DESTROY", 0) == 0:
            zero_destroy_platforms.append((platform, len(sub)))

    total_cells = ["**Total**", str(total_rows)] + [str(total_counts.get(o, 0)) for o in OUTCOMES] + [""]
    lines.append("| " + " | ".join(total_cells) + " |")
    lines.append("")

    if zero_destroy_platforms:
        lines.append("**Flag -- platforms with zero DESTROY (no confirmed successful playback):**")
        for platform, n in zero_destroy_platforms:
            lines.append(f"- `{platform}` (n={n})")
        lines.append("")
    return "\n".join(lines)


def section_missing(rows, debug_states_rows):
    lines = ["## 7. \"missing (no `unified_sessions` row)\" root-cause check", ""]
    missing = [r for r in rows if outcome_of(r) == "missing"]
    lines.append(f"{len(missing)} sessions ({fmt_pct(len(missing), len(rows))}) have no `playback_outcome`.")
    lines.append("")

    with_sid = [r for r in missing if r.get(SESSION_KEY)]
    without_sid = [r for r in missing if not r.get(SESSION_KEY)]
    lines.append(f"- {len(without_sid)} of these never had a resolvable `sessionId` from the base "
                 f"Lightstep merge (`match_status` shows unmatched) -- never eligible for the Athena "
                 f"join in the first place.")

    if debug_states_rows is None:
        lines.append("- No `debug_states` file supplied (`--debug-states`) -- cannot split the "
                     "remaining missing sessions into coverage-gap vs. no-trace-at-all. Re-run with "
                     "`--debug-states data/athena/YYYY-MM-DD_debug_states.csv` to complete this check.")
        lines.append("")
        return "\n".join(lines)

    debug_sids = defaultdict(list)
    for r in debug_states_rows:
        sid = r.get(SESSION_KEY, "")
        if sid:
            debug_sids[sid].append(r)

    sids = [r.get(SESSION_KEY) for r in with_sid]
    found = [sid for sid in sids if sid in debug_sids]
    not_found = [sid for sid in sids if sid not in debug_sids]

    lines.append(f"- **(a) Coverage gap -- has real events in debug_states:** {len(found)} sessions.")
    reached_destroy = [sid for sid in found if any((e.get("state") or "") == "DESTROY" for e in debug_sids[sid])]
    lines.append(f"  Of these, {len(reached_destroy)} reached `DESTROY` in the debug-events timeline "
                 f"(a real `unified_sessions` coverage gap); the rest are short-lived/abandoned "
                 f"fragments (`CREATE` only, or partial `BUFFERING`/`PLAYING`).")
    os_mix = Counter((r.get("OS Family", ""), r.get("Browser Name", ""))
                     for r in with_sid if r.get(SESSION_KEY) in found)
    lines.append(f"  OS/Browser mix: {dict(os_mix)}")
    lines.append("")

    lines.append(f"- **(b) No trace in either Athena table:** {len(not_found)} sessions -- "
                 f"early-failure / non-browser client / telemetry-gap candidates.")
    os_mix_b = Counter((r.get("OS Family", ""), r.get("Browser Name", ""))
                       for r in with_sid if r.get(SESSION_KEY) in not_found)
    lines.append(f"  OS/Browser mix: {dict(os_mix_b)}")
    lines.append("")

    times = [r.get("start_time") for r in with_sid if r.get("start_time")]
    if times:
        times_sorted = sorted(times)
        lines.append(f"**Day-boundary check:** missing-session timestamps span "
                     f"`{times_sorted[0]}` to `{times_sorted[-1]}`. Check whether these cluster "
                     f"near midnight (partition-cutoff signal) or spread across the day (genuine "
                     f"coverage gap) before concluding which it is.")
        lines.append("")

    full_os_mix = Counter((r.get("OS Family", ""), r.get("Browser Name", "")) for r in missing)
    lines.append(f"**OS/Browser mix of the full missing group ({len(missing)}):** {dict(full_os_mix)}")
    lines.append("")
    return "\n".join(lines)


def section_household(rows):
    lines = ["## 8. `householdId` pattern check", ""]
    nonstd = [r for r in rows if r.get("householdId") and not HOUSEHOLD_ID_RE.match(r["householdId"])]
    total_with_hh = sum(1 for r in rows if r.get("householdId"))
    lines.append(f"{len(nonstd)} non-standard `householdId` value(s) found "
                 f"(out of {total_with_hh} rows with a householdId).")
    lines.append("")

    if not nonstd:
        lines.append("No non-standard householdId patterns detected -- all match the opaque "
                     "~52-char token format.")
        lines.append("")
        return "\n".join(lines)

    by_hh = defaultdict(list)
    for r in nonstd:
        by_hh[r["householdId"]].append(r)

    lines.append("| householdId | Sessions | Platform | Browser Name | IP | Outcome mix |")
    lines.append("|---|---|---|---|---|---|")
    ip_to_hh = defaultdict(set)
    for hh, sub in by_hh.items():
        platforms = Counter(r.get("Platform", "") for r in sub)
        browsers = Counter(r.get("Browser Name", "") for r in sub)
        ips = Counter(r.get("session.clientIp", "") for r in sub)
        outcomes = Counter(outcome_of(r) for r in sub)
        for ip in ips:
            ip_to_hh[ip].add(hh)

        plat_str = ", ".join(f"{p} ({c})" for p, c in platforms.items())
        browser_str = ", ".join(f"{b} ({c})" for b, c in browsers.items())
        ip_str = ", ".join(f"{ip} ({c})" for ip, c in ips.items())
        outcome_str = ", ".join(f"{o} ({c})" for o, c in outcomes.items())
        lines.append(f"| `{hh}` | {len(sub)} | {plat_str} | {browser_str} | {ip_str} | {outcome_str} |")
    lines.append("")

    shared_ips = {ip: hhs for ip, hhs in ip_to_hh.items() if len(hhs) > 1}
    if shared_ips:
        lines.append("**Flag -- IP shared across multiple non-standard householdIds "
                     "(possible shared test/lab device or QA rig):**")
        for ip, hhs in shared_ips.items():
            lines.append(f"- `{ip}`: {', '.join(hhs)}")
        lines.append("")
    return "\n".join(lines)


def build_report(rows, debug_states_rows, date_label, source_path):
    total = len(rows)
    header = [
        f"# Playback Outcome Analysis -- `{os.path.basename(source_path)}`",
        "",
        f"**Source file:** `{source_path}` ({total} sessions)",
        "**Context:** See `docs/STATUS.md`, `BLUEPRINT.md`, `LEGEND.md` and "
        "`queries/QUERY_CATALOG.md` for how `playback_outcome`, error detail, and "
        "`state_sequence` were derived and joined into this report.",
        "",
        "---",
        "",
    ]

    outcome_md, _ = section_outcome_distribution(rows)
    sections = [
        outcome_md,
        "---\n",
        section_buffering(rows),
        "---\n",
        section_startup(rows),
        "---\n",
        section_state_sequence(rows),
        "---\n",
        section_device_browser(rows),
        "---\n",
        section_platform(rows),
        "---\n",
        section_missing(rows, debug_states_rows),
        "---\n",
        section_household(rows),
    ]
    return "\n".join(header) + "\n".join(sections)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 09072026")
    default_output_dir = str(investigation_output_dir())
    default_input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "athena")
    ap.add_argument("--report", default=None,
                    help="Path to YYYY-MM-DD_setupsession_with_outcome.csv "
                         "(default: <output-dir>/YYYY-MM-DD_setupsession_with_outcome.csv)")
    ap.add_argument("--debug-states", default=None,
                    help="Path to YYYY-MM-DD_debug_states.csv, used to cross-check the 'missing' "
                         "category (default: <input-dir>/YYYY-MM-DD_debug_states.csv if present)")
    ap.add_argument("--out", default=None,
                    help="Optional path to save the markdown report (default: print to stdout only)")
    args = ap.parse_args()

    try:
        date_iso = _date_ddmmyyyy_to_iso(args.date)
    except ValueError:
        print(f"ERROR: --date must be DDMMYYYY, got '{args.date}'", file=sys.stderr)
        sys.exit(1)

    report_path = args.report or snapshot_output_path(args.date, "setupsession_with_outcome", output_dir=default_output_dir)
    if not os.path.exists(report_path):
        print(f"ERROR: report file not found: {report_path} "
              f"(run merge_session_outcome.py first)", file=sys.stderr)
        sys.exit(1)
    rows = load_csv(report_path)

    debug_states_path = args.debug_states or os.path.join(
        default_input_dir,
        f"{date_iso}_debug_states.csv",
    )
    debug_states_rows = load_csv(debug_states_path) if os.path.exists(debug_states_path) else None
    if debug_states_rows is None:
        print(f"NOTE: no debug_states file found at {debug_states_path} -- "
              f"§7 'missing' root-cause split will be skipped", file=sys.stderr)

    report_md = build_report(rows, debug_states_rows, args.date, report_path)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            f.write(report_md)
        print(f"Wrote report to {args.out}", file=sys.stderr)
    else:
        print(report_md)


if __name__ == "__main__":
    main()
