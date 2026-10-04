#!/usr/bin/env python3
"""
For every deviceId that has a WebView ("; wv") session on a given
source date's output/YYYY-MM-DD_setupsession_with_outcome.csv report,
scans *every* YYYY-MM-DD_setupsession_with_outcome.csv file in
--input-dir (i.e. every date this pipeline has been run for) for that
same deviceId, and reports each session found: its date, raw
User-Agent, whether that UA is the same wv UA as the source date (or a
different UA -- wv or not), and whether playback succeeded
(playback_outcome == "DESTROY").

This answers the recurring manual question "pick a wv=true deviceId --
does it ever use a different user-agent on some other date, and did
playback succeed in that other UA?" without re-doing the pandas
one-off each time. Reuses the wv-detection helper (`_is_wv`, keyed off
the parsed User-Agent `Platform` column) from analyze_webview_devices.py
so both scripts agree on what counts as a WebView session.

Writes one row per (deviceId, session) across all dates found to
output/YYYY-MM-DD_wv_device_cross_date_history.csv (date = the source
date the wv deviceIds were selected from).

Usage:
    python3 analyze_wv_device_cross_date_success.py --date 18092026
    python3 analyze_wv_device_cross_date_success.py --date 18092026 \
        --input-dir ../output --output-dir ../output
"""
import argparse
import logging
from lib import csv_io_compat as csv
import glob
import os
import re
import sys
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_wv_device_cross_date_success")

from analyze_webview_devices import _is_wv, _is_success
from lib.runtime import investigation_output_dir, snapshot_output_path

FILE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_setupsession_with_outcome\.csv$")

OUTPUT_COLUMNS = [
    "deviceId", "source_wv_user_agent",
    "history_date", "sessionId", "raw_user_agent",
    "is_wv", "is_same_ua_as_source", "playback_outcome", "is_success",
]


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


def find_source_wv_devices(source_date, input_dir):
    """Returns {deviceId: source_wv_raw_user_agent} for every wv session
    in the source date's report."""
    source_path = snapshot_output_path(source_date, "setupsession_with_outcome", output_dir=input_dir)
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"source date input file not found: {source_path}")
    rows = load_rows(source_path)
    if rows is None:
        raise ValueError(f"source date input file {source_path} missing required columns")

    wv_devices = {}
    for row in rows:
        if _is_wv(row):
            wv_devices.setdefault(row["deviceId"], row["raw_user_agent"])
    return wv_devices


def build_history_rows(wv_devices, input_dir):
    """Scans every YYYY-MM-DD_setupsession_with_outcome.csv in input_dir
    for sessions belonging to any deviceId in `wv_devices`, returning
    one output row per (deviceId, session) found, across all dates."""
    out_rows = []
    files = sorted(glob.glob(os.path.join(input_dir, "*_setupsession_with_outcome.csv")))
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
            if device_id not in wv_devices:
                continue
            source_ua = wv_devices[device_id]
            raw_ua = row.get("raw_user_agent", "")
            out_rows.append({
                "deviceId": device_id,
                "source_wv_user_agent": source_ua,
                "history_date": file_date,
                "sessionId": row.get("sessionId", ""),
                "raw_user_agent": raw_ua,
                "is_wv": _is_wv(row),
                "is_same_ua_as_source": raw_ua == source_ua,
                "playback_outcome": row.get("playback_outcome", ""),
                "is_success": _is_success(row),
            })
    return out_rows


def main():
    init_logging("ctap-smvod-analyze_wv_device_cross_date_success")
    LOGGER.info("Starting analyze_wv_device_cross_date_success")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True,
                    help="Source date (DDMMYYYY) to pick wv=true deviceIds from, e.g. 18092026")
    default_dir = str(investigation_output_dir())
    ap.add_argument("--input-dir", default=default_dir,
                    help=f"Directory containing YYYY-MM-DD_setupsession_with_outcome.csv files "
                         f"for every date to search (default: {default_dir})")
    ap.add_argument("--output-dir", default=default_dir,
                    help=f"Directory to write YYYY-MM-DD_wv_device_cross_date_history.csv into "
                         f"(default: {default_dir})")
    ap.add_argument("--out", default=None, help="Explicit output path override")
    args = ap.parse_args()

    wv_devices = find_source_wv_devices(args.date, args.input_dir)
    if not wv_devices:
        print(f"No wv=true deviceIds found in {args.date} report -- nothing to do.", file=sys.stderr)
        sys.exit(0)

    out_rows = build_history_rows(wv_devices, args.input_dir)

    out_path = args.out or snapshot_output_path(args.date, "wv_device_cross_date_history", output_dir=args.output_dir)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    other_ua_rows = [r for r in out_rows if not r["is_same_ua_as_source"]]
    other_ua_success = [r for r in other_ua_rows if r["is_success"]]
    print(f"{args.date}: {len(wv_devices)} wv deviceId(s) found; "
          f"{len(out_rows)} total session row(s) across all dates written to {out_path}",
          file=sys.stderr)
    print(f"  {len(other_ua_rows)} session(s) used a DIFFERENT user-agent than the source wv UA; "
          f"{len(other_ua_success)} of those succeeded (DESTROY).", file=sys.stderr)
    for r in other_ua_success:
        print(f"    deviceId={r['deviceId']} date={r['history_date']} session={r['sessionId']} "
              f"ua={r['raw_user_agent']}", file=sys.stderr)

    LOGGER.info(
        "Completed analyze_wv_device_cross_date_success devices=%d rows=%d out=%s",
        len(wv_devices),
        len(out_rows),
        out_path,
    )


if __name__ == "__main__":
    main()
