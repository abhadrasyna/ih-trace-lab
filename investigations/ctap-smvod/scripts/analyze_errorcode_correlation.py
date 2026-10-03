#!/usr/bin/env python3
"""Analyze correlation between a specific PLAYER_ERROR errorcode and
household / content / device attributes.

Input 1: a raw Athena export of unified_e6auj7k7.e6auj7k7_ccl_debug_events
rows for a single errorcode (columns: datetime, messageid, clibversion,
clientid, eventclass, eventid, eventdata), as saved under
queries/exploration/.

Input 2: one or more output/setupsession_with_outcome_<DDMMYYYY>.csv files
(Stage 2 merge output), used to look up householdId / contentId /
externalPackageId / deviceId for each sessionId that appears in Input 1.
Only dates with a matching merged output file will resolve household/
content info; other sessionIds are reported as "no merged output for date".

Usage:
    python3 analyze_errorcode_correlation.py \
        --errors ../queries/exploration/errorcode_3016_raw_08012026_08312026.csv \
        --output-dir ../output

Prints frequency breakdowns (top households, top content, top devices/app
versions) to stdout. Does not write any files.
"""
import argparse
from lib import csv_io_compat as csv
import glob
import json
import os
import re
from collections import Counter, defaultdict

SESSION_FIELDS = ["householdId", "deviceId", "contentId", "externalPackageId"]


def load_session_lookup(output_dir):
    """Build sessionId -> dict(householdId, deviceId, contentId, externalPackageId)
    from every setupsession_with_outcome_*.csv found in output_dir."""
    lookup = {}
    pattern = os.path.join(output_dir, "setupsession_with_outcome_*.csv")
    for path in sorted(glob.glob(pattern)):
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = row.get("sessionId")
                if not sid:
                    continue
                lookup[sid] = {k: row.get(k, "") for k in SESSION_FIELDS}
    return lookup


def parse_error_rows(errors_csv):
    """Yield (day, sessionid, clientid, app_version, user_agent, message) per row."""
    with open(errors_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = row.get("datetime", "")
            day = dt[:10] if dt else "unknown"
            try:
                ed = json.loads(row["eventdata"])
            except (KeyError, json.JSONDecodeError):
                continue
            sessionid = ed.get("sessionid", "")
            errdesc = ed.get("errordescription", {}) or {}
            # errordescription is usually a nested object, but some rows
            # have it as a plain string (older/alternate event shape) --
            # tolerate both instead of hard-erroring.
            if not isinstance(errdesc, dict):
                errdesc = {}
            app_version = errdesc.get("app_version", "")
            user_agent = errdesc.get("user_agent", "")
            shaka = errdesc.get("shakaerror", {}) or {}
            if not isinstance(shaka, dict):
                shaka = {}
            message = shaka.get("message", "")
            yield day, sessionid, row.get("clientid", ""), app_version, user_agent, message


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--errors", required=True, help="Path to raw errorcode export CSV")
    ap.add_argument("--output-dir", default="../output", help="Dir with setupsession_with_outcome_*.csv")
    ap.add_argument("--top", type=int, default=15, help="Rows to show per breakdown")
    args = ap.parse_args()

    lookup = load_session_lookup(args.output_dir)

    total_rows = 0
    sessions_seen = set()
    by_day = Counter()
    household_counter = Counter()
    content_counter = Counter()
    device_counter = Counter()
    app_version_counter = Counter()
    message_counter = Counter()
    unresolved_sessions = 0

    for day, sessionid, clientid, app_version, user_agent, message in parse_error_rows(args.errors):
        total_rows += 1
        by_day[day] += 1
        app_version_counter[app_version] += 1
        message_counter[message] += 1
        sessions_seen.add(sessionid)

        info = lookup.get(sessionid)
        if info:
            if info["householdId"]:
                household_counter[info["householdId"]] += 1
            if info["contentId"]:
                content_counter[info["contentId"]] += 1
            if info["deviceId"]:
                device_counter[info["deviceId"]] += 1
        else:
            unresolved_sessions += 1

    print(f"Total error rows: {total_rows}")
    print(f"Unique sessionids: {len(sessions_seen)}")
    print(f"Sessions with NO matching setupsession_with_outcome row "
          f"(likely no merged output for that date): {unresolved_sessions} rows\n")

    print("=== Errors by day ===")
    for day, cnt in sorted(by_day.items()):
        print(f"  {day}: {cnt}")

    print(f"\n=== Top {args.top} households (by error-row count) ===")
    for hh, cnt in household_counter.most_common(args.top):
        print(f"  {cnt:4d}  {hh}")
    if not household_counter:
        print("  (no households resolved -- no merged output covers these sessionIds)")

    print(f"\n=== Top {args.top} contentIds (by error-row count) ===")
    for cid, cnt in content_counter.most_common(args.top):
        print(f"  {cnt:4d}  {cid}")
    if not content_counter:
        print("  (no contentIds resolved -- no merged output covers these sessionIds)")

    print(f"\n=== Top {args.top} deviceIds (by error-row count) ===")
    for did, cnt in device_counter.most_common(args.top):
        print(f"  {cnt:4d}  {did}")

    print(f"\n=== App versions ===")
    for av, cnt in app_version_counter.most_common(args.top):
        print(f"  {cnt:4d}  {av}")

    print(f"\n=== Distinct shaka error messages ===")
    for msg, cnt in message_counter.most_common(args.top):
        print(f"  {cnt:4d}  {msg}")


if __name__ == "__main__":
    main()
