#!/usr/bin/env python3
"""
Consolidates the per-date output/mtn_escalation_ips_DDMMYYYY.csv files
(produced by correlate_cdn_ips.py) into two summary CSVs in output/, so
MTN-escalation evidence lives as durable data files rather than as prose
in docs/STATUS.md.

Writes:
  output/mtn_escalation_all_dates.csv
      Union of every escalation-candidate session across all dates, with
      a `date` column added, sorted by clientIp then start_time. This is
      the "gather the qualifying examples" artifact for docs/STATUS.md's
      MTN escalation criteria / for sharing with MTN.

  output/mtn_escalation_by_ip_summary.csv
      One row per IP: how many escalation sessions, which dates it
      appeared on, breakdown by root-cause hint, and a `repeat_offender`
      flag (seen on 2+ distinct dates) -- the IPs most worth flagging to
      MTN's network team first.

Usage:
    python3 build_mtn_summary.py [--output-dir ../output]

Run this after (re-)running correlate_cdn_ips.py for any date, to keep
the consolidated files in sync. See docs/STATUS.md ("MTN network-team
escalation criteria") for the underlying trigger/process this supports.
"""
import argparse
from lib import csv_io_compat as csv
import glob
import os
import re
from collections import defaultdict

FILE_RE = re.compile(r'mtn_escalation_ips_(\d{8})\.csv$')


def date_to_iso(ddmmyyyy):
    return f"{ddmmyyyy[4:8]}-{ddmmyyyy[2:4]}-{ddmmyyyy[0:2]}"


def build_summary(output_dir):
    files = sorted(glob.glob(os.path.join(output_dir, "mtn_escalation_ips_*.csv")))
    all_rows = []
    for path in files:
        m = FILE_RE.search(os.path.basename(path))
        if not m:
            continue
        date = date_to_iso(m.group(1))
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                row['date'] = date
                all_rows.append(row)

    if not all_rows:
        print("No mtn_escalation_ips_*.csv files found -- nothing to summarize.")
        return

    all_rows.sort(key=lambda r: (r['clientIp'], r['start_time']))

    all_dates_path = os.path.join(output_dir, "mtn_escalation_all_dates.csv")
    fieldnames = ["date"] + [k for k in all_rows[0].keys() if k != 'date']
    with open(all_dates_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {all_dates_path}: {len(all_rows)} escalation-candidate sessions "
          f"across {len(files)} date file(s)")

    by_ip = defaultdict(lambda: {"dates": set(), "sessions": 0, "hints": defaultdict(int)})
    for r in all_rows:
        entry = by_ip[r['clientIp']]
        entry["dates"].add(r['date'])
        entry["sessions"] += 1
        hint = r['root_cause_hint'].split(" (")[0]
        entry["hints"][hint] += 1

    summary_rows = []
    for ip, entry in by_ip.items():
        dates_sorted = sorted(entry["dates"])
        summary_rows.append({
            "clientIp": ip,
            "escalation_session_count": entry["sessions"],
            "distinct_dates_seen": len(dates_sorted),
            "dates_seen": ";".join(dates_sorted),
            "repeat_offender": "yes" if len(dates_sorted) > 1 else "no",
            "hint_breakdown": ";".join(f"{k}={v}" for k, v in sorted(entry["hints"].items())),
        })
    summary_rows.sort(key=lambda r: (-r["distinct_dates_seen"], -r["escalation_session_count"], r["clientIp"]))

    by_ip_path = os.path.join(output_dir, "mtn_escalation_by_ip_summary.csv")
    with open(by_ip_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    repeat_offenders = [r for r in summary_rows if r["repeat_offender"] == "yes"]
    print(f"Wrote {by_ip_path}: {len(summary_rows)} unique IP(s), "
          f"{len(repeat_offenders)} repeat offender(s) (seen on 2+ dates)")
    for r in repeat_offenders:
        print(f"  repeat offender: {r['clientIp']} -- {r['escalation_session_count']} sessions "
              f"on {r['dates_seen']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output-dir', default='../output', help='Directory containing mtn_escalation_ips_*.csv (default: ../output)')
    args = ap.parse_args()
    build_summary(args.output_dir)


if __name__ == '__main__':
    main()
