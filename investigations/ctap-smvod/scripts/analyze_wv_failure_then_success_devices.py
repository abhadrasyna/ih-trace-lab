#!/usr/bin/env python3
"""
Scans every output/setupsession_with_outcome_DDMMYYYY.csv file
available (the full date range this pipeline has been run for) and
finds every deviceId that had at least one WebView ("; wv") playback
*failure* (playback_outcome != "DESTROY") on some date, but also had
at least one *successful* playback (playback_outcome == "DESTROY", on
any user-agent -- wv or not) on a *different* date.

deviceId is the join key across dates/files -- this answers "which
devices failed on WebView on one day but proved they can play back
successfully on another day" in one pass, generalizing the manual
per-date wv checks done via analyze_wv_device_cross_date_success.py.

Reuses _is_wv/_is_success from analyze_webview_devices.py so wv
detection and success detection stay consistent across all three
scripts.

Writes one row per deviceId (only devices matching the
failure-then-success-elsewhere pattern) to
output/wv_failure_then_success_report.csv, plus a raw evidence CSV
(output/wv_failure_then_success_evidence.csv) with one row per
underlying session so the failure/success dates and UAs can be
inspected directly.

Usage:
    python3 analyze_wv_failure_then_success_devices.py
    python3 analyze_wv_failure_then_success_devices.py --input-dir ../output --output-dir ../output
"""
import argparse
from lib import csv_io_compat as csv
import glob
import os
import re
import sys
from collections import defaultdict

from analyze_webview_devices import _is_wv, _is_success

FILE_RE = re.compile(r"setupsession_with_outcome_(\d{8})\.csv$")

REPORT_COLUMNS = [
    "deviceId",
    "wv_failure_dates", "wv_failure_count",
    "success_dates", "success_count",
    "first_wv_failure_date", "first_success_date",
    "success_seen_on_wv", "success_seen_on_non_wv",
]

EVIDENCE_COLUMNS = [
    "deviceId", "date", "sessionId", "raw_user_agent",
    "is_wv", "is_success", "playback_outcome",
]


def _ddmmyyyy_sort_key(d):
    """DDMMYYYY -> (YYYY, MM, DD) so dates sort chronologically."""
    return (d[4:8], d[2:4], d[0:2])


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        required = ["sessionId", "deviceId", "Platform", "raw_user_agent", "playback_outcome"]
        missing = [c for c in required if c not in available]
        if missing:
            print(f"WARNING: skipping {path} -- required column(s) {missing} not found "
                  f"(run merge_session_outcome.py first). Available columns: {available}",
                  file=sys.stderr)
            return None
        return list(reader)


def collect_all_sessions(input_dir):
    """Returns {deviceId: [ (date, row_dict), ... ]}, one entry per
    session found across every setupsession_with_outcome_*.csv in
    input_dir, sorted chronologically per device."""
    by_device = defaultdict(list)
    files = sorted(glob.glob(os.path.join(input_dir, "setupsession_with_outcome_*.csv")))
    for path in files:
        m = FILE_RE.search(os.path.basename(path))
        if not m:
            continue
        file_date = m.group(1)
        rows = load_rows(path)
        if rows is None:
            continue
        for row in rows:
            device_id = row.get("deviceId", "")
            if device_id:
                by_device[device_id].append((file_date, row))

    for device_id in by_device:
        by_device[device_id].sort(key=lambda t: _ddmmyyyy_sort_key(t[0]))
    return by_device


def find_failure_then_success_devices(by_device):
    """Returns (report_rows, evidence_rows) for every deviceId with a
    wv failure on one date and a success (any UA) on a different
    date."""
    report_rows = []
    evidence_rows = []

    for device_id, sessions in by_device.items():
        failure_dates = sorted({d for d, r in sessions if _is_wv(r) and not _is_success(r)},
                                key=_ddmmyyyy_sort_key)
        if not failure_dates:
            continue

        success_entries = [(d, r) for d, r in sessions if _is_success(r) and d not in failure_dates]
        # A device might have both a wv failure AND a success on the *same*
        # date (different sessions) -- that still counts as "succeeded on a
        # different date" only if the success date differs from *every*
        # failure date; sessions sharing a failure date are excluded above
        # to keep the "different date" requirement strict.
        if not success_entries:
            continue

        success_dates = sorted({d for d, r in success_entries}, key=_ddmmyyyy_sort_key)
        success_seen_on_wv = any(_is_wv(r) for _, r in success_entries)
        success_seen_on_non_wv = any(not _is_wv(r) for _, r in success_entries)

        report_rows.append({
            "deviceId": device_id,
            "wv_failure_dates": ";".join(failure_dates),
            "wv_failure_count": len(failure_dates),
            "success_dates": ";".join(success_dates),
            "success_count": len(success_dates),
            "first_wv_failure_date": failure_dates[0],
            "first_success_date": success_dates[0],
            "success_seen_on_wv": success_seen_on_wv,
            "success_seen_on_non_wv": success_seen_on_non_wv,
        })

        for d, r in sessions:
            is_wv = _is_wv(r)
            is_success = _is_success(r)
            if (is_wv and not is_success) or is_success:
                evidence_rows.append({
                    "deviceId": device_id,
                    "date": d,
                    "sessionId": r.get("sessionId", ""),
                    "raw_user_agent": r.get("raw_user_agent", ""),
                    "is_wv": is_wv,
                    "is_success": is_success,
                    "playback_outcome": r.get("playback_outcome", ""),
                })

    report_rows.sort(key=lambda r: _ddmmyyyy_sort_key(r["first_wv_failure_date"]))
    return report_rows, evidence_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    ap.add_argument("--input-dir", default=default_dir,
                    help=f"Directory containing setupsession_with_outcome_DDMMYYYY.csv files "
                         f"for every date to search (default: {default_dir})")
    ap.add_argument("--output-dir", default=default_dir,
                    help=f"Directory to write the report/evidence CSVs into (default: {default_dir})")
    args = ap.parse_args()

    by_device = collect_all_sessions(args.input_dir)
    report_rows, evidence_rows = find_failure_then_success_devices(by_device)

    report_path = os.path.join(args.output_dir, "wv_failure_then_success_report.csv")
    evidence_path = os.path.join(args.output_dir, "wv_failure_then_success_evidence.csv")

    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(report_rows)

    with open(evidence_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_COLUMNS)
        writer.writeheader()
        writer.writerows(evidence_rows)

    print(f"Scanned {len(by_device)} distinct deviceId(s) across all available dates.", file=sys.stderr)
    print(f"{len(report_rows)} deviceId(s) had a wv failure on one date and a success "
          f"(any UA) on a different date -- written to {report_path}", file=sys.stderr)
    print(f"Evidence ({len(evidence_rows)} session rows) written to {evidence_path}", file=sys.stderr)
    for r in report_rows:
        print(f"  deviceId={r['deviceId']} first_failure={r['first_wv_failure_date']} "
              f"first_success={r['first_success_date']} "
              f"(wv_failures={r['wv_failure_count']} success_dates={r['success_count']})",
              file=sys.stderr)


if __name__ == "__main__":
    main()
