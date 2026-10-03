#!/usr/bin/env python3
"""
Consolidates the per-date output/webview_device_report_DDMMYYYY.csv
files (produced by analyze_webview_devices.py) into a single
device-model-level summary CSV in output/, so the "which device models
have unreliable WebView playback" question can be answered across the
whole date range in one place, without changing the per-date report
convention (analyze_webview_devices.py deliberately never merges those
-- see BLUEPRINT.md).

Each webview_device_report_DDMMYYYY.csv row is one wv *session*, with
device-level wv/non-wv aggregate counts repeated on every row for that
deviceId on that date (see analyze_webview_devices.py). To roll this up
by device_model across dates without double-counting the repeated
per-deviceId aggregate columns, this script:

  1. Counts wv success/failure directly from the session-level rows
     (each row = one wv session), grouped by device_model.
  2. Deduplicates to one (date, deviceId) combination before summing
     the device_non_wv_* columns, since those are device/date
     aggregates repeated across every wv row for that device that day.

Writes:
  output/webview_device_summary_report.csv
      One row per device_model: total wv sessions/success/failure and
      wv success rate across all dates found, how many distinct
      deviceIds of that model appeared, how many dates it appeared on,
      and the same success/failure/rate breakdown for that model's
      *non*-wv sessions (i.e. did the same device model succeed when
      NOT using WebView) plus a `non_wv_success_when_wv_failed_flag`
      hinting whether non-wv playback worked despite wv failures.

Usage:
    python3 build_webview_device_summary.py
    python3 build_webview_device_summary.py --output-dir ../output
"""
import argparse
from lib import csv_io_compat as csv
import glob
import os
import re
from collections import defaultdict

FILE_RE = re.compile(r'webview_device_report_(\d{8})\.csv$')


def date_to_iso(ddmmyyyy):
    return f"{ddmmyyyy[4:8]}-{ddmmyyyy[2:4]}-{ddmmyyyy[0:2]}"


def load_rows(output_dir):
    """Reads every webview_device_report_DDMMYYYY.csv in output_dir,
    tagging each row with its source `date` (ISO) so downstream dedup/
    aggregation can key on (date, deviceId)."""
    files = sorted(glob.glob(os.path.join(output_dir, "webview_device_report_*.csv")))
    all_rows = []
    for path in files:
        m = FILE_RE.search(os.path.basename(path))
        if not m:
            continue
        iso_date = date_to_iso(m.group(1))
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                row['date'] = iso_date
                all_rows.append(row)
    return all_rows


def build_summary_rows(all_rows):
    """Returns the list of per-device_model summary row dicts."""
    by_model = defaultdict(lambda: {
        'device_ids': set(),
        'dates': set(),
        'wv_success': 0,
        'wv_failure': 0,
    })
    # Dedup key for the repeated per-deviceId/date non-wv aggregate
    # columns: only count each (date, deviceId) combo once.
    seen_device_date = set()
    non_wv_by_model = defaultdict(lambda: {'success': 0, 'failure': 0})

    for row in all_rows:
        model = row.get('device_model', '') or '(unknown)'
        device_id = row.get('deviceId', '')
        iso_date = row.get('date', '')

        entry = by_model[model]
        entry['device_ids'].add(device_id)
        entry['dates'].add(iso_date)
        if (row.get('is_success') or '').strip().lower() == 'true':
            entry['wv_success'] += 1
        else:
            entry['wv_failure'] += 1

        dedup_key = (iso_date, device_id)
        if dedup_key not in seen_device_date:
            seen_device_date.add(dedup_key)
            non_wv = non_wv_by_model[model]
            non_wv['success'] += int(row.get('device_non_wv_success_count', 0) or 0)
            non_wv['failure'] += int(row.get('device_non_wv_failure_count', 0) or 0)

    out_rows = []
    for model, entry in sorted(by_model.items(), key=lambda kv: kv[0]):
        wv_total = entry['wv_success'] + entry['wv_failure']
        non_wv = non_wv_by_model[model]
        non_wv_total = non_wv['success'] + non_wv['failure']

        out_rows.append({
            'device_model': model,
            'distinct_device_count': len(entry['device_ids']),
            'dates_seen_count': len(entry['dates']),
            'date_range': ','.join(sorted(entry['dates'])),
            'wv_session_count': wv_total,
            'wv_success_count': entry['wv_success'],
            'wv_failure_count': entry['wv_failure'],
            'wv_success_rate_pct': round(100 * entry['wv_success'] / wv_total, 1) if wv_total else '',
            'non_wv_session_count': non_wv_total,
            'non_wv_success_count': non_wv['success'],
            'non_wv_failure_count': non_wv['failure'],
            'non_wv_success_rate_pct': round(100 * non_wv['success'] / non_wv_total, 1) if non_wv_total else '',
            'non_wv_success_when_wv_failed_flag': entry['wv_failure'] > 0 and non_wv['success'] > 0,
        })
    return out_rows


SUMMARY_COLUMNS = [
    'device_model', 'distinct_device_count', 'dates_seen_count', 'date_range',
    'wv_session_count', 'wv_success_count', 'wv_failure_count', 'wv_success_rate_pct',
    'non_wv_session_count', 'non_wv_success_count', 'non_wv_failure_count', 'non_wv_success_rate_pct',
    'non_wv_success_when_wv_failed_flag',
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    ap.add_argument("--output-dir", default=default_dir,
                    help=f"Directory containing webview_device_report_DDMMYYYY.csv files and to "
                         f"write the summary into (default: {default_dir})")
    args = ap.parse_args()

    all_rows = load_rows(args.output_dir)
    if not all_rows:
        print("No webview_device_report_*.csv files found -- nothing to summarize.")
        return

    summary_rows = build_summary_rows(all_rows)

    out_path = os.path.join(args.output_dir, "webview_device_summary_report.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)

    dates_covered = sorted({r['date'] for r in all_rows})
    print(f"Summarized {len(all_rows)} wv session rows across {len(dates_covered)} date(s) "
          f"({dates_covered[0]}..{dates_covered[-1]}) into {len(summary_rows)} device_model row(s) "
          f"-> {out_path}")


if __name__ == "__main__":
    main()
