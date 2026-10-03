#!/usr/bin/env python3
"""
Extract a per-device WebView ("wv") reliability report from the final
output/setupsession_with_outcome_DDMMYYYY.csv report (produced by
merge_session_outcome.py).

For every session whose parsed User-Agent `Platform` column ends in
"; wv" (Android's WebView token -- see docs/STATUS.md discussion), this
pulls out the device model/Android version/build id embedded in that
Platform string, flags whether the session's playback_outcome was a
confirmed success (DESTROY), and -- per deviceId -- reports how many of
that device's *other* wv sessions succeeded/failed
(`device_has_mixed_results`) as well as whether that same deviceId also
has non-wv sessions this date (`device_has_non_wv_sessions`), and their
own success/failure split.

Deliberately does NOT collapse a date range into one combined CSV --
each date in --start-date/--end-date gets its own independent
output/webview_device_report_DDMMYYYY.csv, matching this project's
per-date output file convention (see BLUEPRINT.md). Missing daily input
files are skipped with a stderr warning rather than failing the whole
range, same convention as filter_error_code_report.py.

Usage:
    # Single date
    python3 analyze_webview_devices.py --date 18092026

    # Date range (inclusive), one output CSV per date -- not merged
    python3 analyze_webview_devices.py --start-date 2026-09-01 --end-date 2026-09-10

    python3 analyze_webview_devices.py --date 18092026 \
        --input ../output/setupsession_with_outcome_18092026.csv \
        --out ../output/webview_device_report_18092026.csv
"""
import argparse
from lib import csv_io_compat as csv
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

# Matches the Android WebView UA's build segment, e.g.
# "Android 15; SM-A055F Build/AP3A.240905.015.A2; wv" -> model=SM-A055F,
# android=15, build=AP3A.240905.015.A2. Model is captured non-greedily up
# to " Build/" and build stops at the next ';' (there's always a
# trailing "; wv" after it) so neither field picks up extra tokens.
UA_RE = re.compile(r"Android\s+(?P<android>[\d.]+);\s*(?P<model>.+?)\s+Build/(?P<build>[^;]+)")

OUTPUT_COLUMNS = [
    "sessionId", "deviceId", "content",
    "device_model", "android_version", "build_id",
    "playback_outcome", "is_success",
    "device_wv_session_count", "device_wv_success_count", "device_wv_failure_count",
    "device_has_mixed_results",
    "device_non_wv_session_count", "device_non_wv_success_count", "device_non_wv_failure_count",
    "device_has_non_wv_sessions",
]


def _is_wv(row):
    """True if this row's parsed User-Agent Platform column carries the
    Android WebView token (always the last "; wv" segment before the
    closing paren in a WebView UA string)."""
    return (row.get("Platform") or "").strip().lower().endswith("; wv")


def _is_success(row):
    return (row.get("playback_outcome") or "").strip() == "DESTROY"


def _is_failure(row):
    outcome = (row.get("playback_outcome") or "").strip()
    return bool(outcome) and outcome != "DESTROY"


def _parse_ua_fields(platform):
    m = UA_RE.search(platform or "")
    if not m:
        return "", "", ""
    return m.group("model"), m.group("android"), m.group("build")


def build_report_rows(source_rows):
    """Returns the list of output rows (dicts, OUTPUT_COLUMNS keys) for
    the wv subset of `source_rows`, enriched with per-deviceId wv and
    non-wv aggregate counts."""
    by_device_all = defaultdict(list)
    for row in source_rows:
        device_id = (row.get("deviceId") or "").strip()
        if device_id:
            by_device_all[device_id].append(row)

    out_rows = []
    for row in source_rows:
        if not _is_wv(row):
            continue

        device_id = (row.get("deviceId") or "").strip()
        if not device_id:
            device_rows = [row]
        else:
            device_rows = by_device_all.get(device_id, [])
        wv_rows = [r for r in device_rows if _is_wv(r)]
        non_wv_rows = [r for r in device_rows if not _is_wv(r)]

        wv_success = sum(1 for r in wv_rows if _is_success(r))
        wv_failure = sum(1 for r in wv_rows if _is_failure(r))
        non_wv_success = sum(1 for r in non_wv_rows if _is_success(r))
        non_wv_failure = sum(1 for r in non_wv_rows if _is_failure(r))

        model, android_version, build_id = _parse_ua_fields(row.get("Platform", ""))

        out_rows.append({
            "sessionId": row.get("sessionId", ""),
            "deviceId": device_id,
            "content": row.get("content", ""),
            "device_model": model,
            "android_version": android_version,
            "build_id": build_id,
            "playback_outcome": row.get("playback_outcome", ""),
            "is_success": _is_success(row),
            "device_wv_session_count": len(wv_rows),
            "device_wv_success_count": wv_success,
            "device_wv_failure_count": wv_failure,
            "device_has_mixed_results": wv_success > 0 and wv_failure > 0,
            "device_non_wv_session_count": len(non_wv_rows),
            "device_non_wv_success_count": non_wv_success,
            "device_non_wv_failure_count": non_wv_failure,
            "device_has_non_wv_sessions": len(non_wv_rows) > 0,
        })
    return out_rows


def process_one_date(date_ddmmyyyy, input_dir, output_dir, out_override=None):
    """Processes one DDMMYYYY date and returns a `(status, written_rows)` tuple."""
    input_path = os.path.join(input_dir, f"setupsession_with_outcome_{date_ddmmyyyy}.csv")
    if not os.path.exists(input_path):
        print(f"WARNING: skipping {date_ddmmyyyy} -- input file not found: {input_path}",
              file=sys.stderr)
        return "missing_input", 0

    with open(input_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        required = ["sessionId", "deviceId", "Platform", "playback_outcome"]
        missing = [c for c in required if c not in available]
        if missing:
            print(f"WARNING: skipping {date_ddmmyyyy} -- required column(s) {missing} "
                  f"not found in {input_path} (run merge_session_outcome.py first). "
                  f"Available columns: {available}", file=sys.stderr)
            return "missing_columns", 0
        source_rows = list(reader)

    out_rows = build_report_rows(source_rows)

    out_path = out_override or os.path.join(output_dir, f"webview_device_report_{date_ddmmyyyy}.csv")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    mixed = sum(1 for r in out_rows if r["device_has_mixed_results"])
    print(f"{date_ddmmyyyy}: wrote {len(out_rows)} wv session rows "
          f"({mixed} from devices with mixed success/failure) to {out_path}", file=sys.stderr)
    return "written", len(out_rows)


def _daterange_ddmmyyyy(start_str, end_str):
    """Yields DDMMYYYY strings for every day from start to end
    (both YYYY-MM-DD, inclusive)."""
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    if end < start:
        raise ValueError(f"--end-date {end_str} is before --start-date {start_str}")
    d = start
    while d <= end:
        yield d.strftime("%d%m%Y")
        d += timedelta(days=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None, help="Single date in DDMMYYYY format, e.g. 18092026")
    ap.add_argument("--start-date", default=None,
                    help="Range start date in YYYY-MM-DD format, e.g. 2026-09-01 (use with --end-date)")
    ap.add_argument("--end-date", default=None,
                    help="Range end date in YYYY-MM-DD format, inclusive, e.g. 2026-09-10")
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    ap.add_argument("--input-dir", default=default_dir,
                    help=f"Directory containing setupsession_with_outcome_DDMMYYYY.csv (default: {default_dir})")
    ap.add_argument("--output-dir", default=default_dir,
                    help=f"Directory to write webview_device_report_DDMMYYYY.csv into (default: {default_dir})")
    ap.add_argument("--out", default=None,
                    help="Explicit output path -- only valid with --date (single-date mode), "
                         "ignored/invalid for a --start-date/--end-date range since each date "
                         "always gets its own file")
    args = ap.parse_args()

    if args.date and (args.start_date or args.end_date):
        print("ERROR: pass either --date or --start-date/--end-date, not both.", file=sys.stderr)
        sys.exit(1)
    if bool(args.start_date) != bool(args.end_date):
        print("ERROR: --start-date and --end-date must be passed together.", file=sys.stderr)
        sys.exit(1)
    if not args.date and not args.start_date:
        print("ERROR: must pass --date DDMMYYYY or --start-date/--end-date YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)
    if args.out and args.start_date:
        print("ERROR: --out is only valid with a single --date, not a date range "
              "(each date in a range always writes its own webview_device_report_DDMMYYYY.csv).",
              file=sys.stderr)
        sys.exit(1)

    if args.date:
        dates = [args.date]
    else:
        dates = list(_daterange_ddmmyyyy(args.start_date, args.end_date))

    processed = 0
    missing_input = 0
    missing_columns = 0
    for d in dates:
        out_override = args.out if (args.date and len(dates) == 1) else None
        status, _ = process_one_date(d, args.input_dir, args.output_dir, out_override)
        if status == "written":
            processed += 1
            continue
        if status == "missing_input":
            missing_input += 1
            continue
        if status == "missing_columns":
            missing_columns += 1

    print(
        f"\nDone: {processed} date(s) written, {missing_input} date(s) skipped for missing input, "
        f"{missing_columns} date(s) skipped for missing columns.",
        file=sys.stderr,
    )
    if processed == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
