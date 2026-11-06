#!/usr/bin/env python3
"""Parse `user_agent` strings out of a flattened PLAYER_ERROR debug-event
export and report device/OS/browser breakdowns, cross-tabbed against the
already-flattened Shaka error fields.

Input: a CSV produced by an Athena query against
unified_e6auj7k7.e6auj7k7_ccl_debug_events that already flattens the
nested `eventdata` JSON into columns (see queries/QUERY_CATALOG.md §22-ish
"all 6001 debug events" query). Expected columns include at least:
    hhid, session_id, error_code, position, error_description,
    shaka_message, shaka_category, shaka_severity, shaka_code,
    player_phase, ready_state, network_state, user_agent, app_version,
    datetime

Rows are deduplicated by session_id before analysis (this debug-events
table is known to contain exact-duplicate rows per the same messageid --
see QUERY_CATALOG.md §4).

Usage:
    python3 parse_debug_user_agents.py \
        --input ../queries/exploration/6001_debug_error_aug.csv \
        --top 15

Prints frequency breakdowns to stdout. Does not write any files.
"""
import argparse
import logging
from lib import csv_io_compat as csv
from collections import Counter
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging
from src.lib.user_agent import parse_user_agent  # noqa: F401  # re-export

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.parse_debug_user_agents")

# parse_user_agent now lives in src/lib/user_agent; re-exported here so existing callers keep working.


def load_deduped_rows(input_csv):
    """Read input_csv and return one row per distinct session_id (first
    occurrence kept), enriched with parsed user_agent fields."""
    seen = {}
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        total_rows = 0
        for row in reader:
            total_rows += 1
            sid = row.get("session_id", "")
            if sid in seen:
                continue
            row.update(parse_user_agent(row.get("user_agent", "")))
            seen[sid] = row
    return list(seen.values()), total_rows


def print_top(title, counter, top):
    print(f"\n=== {title} ===")
    if not counter:
        print("  (no values found)")
        return
    for value, cnt in counter.most_common(top):
        print(f"  {cnt:4d}  {value!r}")


def print_full_table(title, col_label, counter):
    """Print every (value, count) pair, unsorted-by-top-N-limit, as a
    simple two-column table -- used for --full-tables output where the
    caller wants the complete breakdown, not just the top N."""
    print(f"\n=== {title} ===")
    if not counter:
        print("  (no values found)")
        return
    print(f"  {col_label:<55} count")
    print(f"  {'-' * 55} -----")
    for value, cnt in counter.most_common():
        print(f"  {str(value):<55} {cnt:5d}")
    print(f"  {'-' * 55} -----")
    print(f"  {'TOTAL':<55} {sum(counter.values()):5d}")


def main():
    init_logging("ctap-smvod-parse_debug_user_agents")
    LOGGER.info("Starting parse_debug_user_agents")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Path to flattened PLAYER_ERROR debug-event export CSV")
    ap.add_argument("--top", type=int, default=15, help="Rows to show per breakdown")
    ap.add_argument("--full-tables", action="store_true",
                     help="Print complete device_model-vs-count and hhid-vs-unique-session-count "
                          "tables (no top-N truncation) in addition to the standard breakdowns")
    args = ap.parse_args()

    rows, total_rows = load_deduped_rows(args.input)

    hhid_counter = Counter()
    device_model_counter = Counter()
    os_name_counter = Counter()
    os_version_counter = Counter()
    chrome_version_counter = Counter()
    webview_counter = Counter()
    shaka_message_counter = Counter()
    player_phase_counter = Counter()
    hhid_device_pairs = set()

    for row in rows:
        hhid = row.get("hhid", "")
        if hhid:
            hhid_counter[hhid] += 1
        device_model_counter[row["device_model"] or "(unparsed)"] += 1
        os_name_counter[row["os_name"] or "(unparsed)"] += 1
        os_version_counter[row["os_version"] or "(unparsed)"] += 1
        chrome_version_counter[row["chrome_version"] or "(unparsed)"] += 1
        webview_counter[row["is_webview"]] += 1
        shaka_message_counter[row.get("shaka_message", "")] += 1
        player_phase_counter[row.get("player_phase", "")] += 1
        if hhid and row["device_model"]:
            hhid_device_pairs.add((hhid, row["device_model"]))

    print(f"Total raw rows: {total_rows}")
    print(f"Distinct session_ids (deduped): {len(rows)}")
    print(f"Distinct (hhid, device_model) pairs: {len(hhid_device_pairs)}")

    print_top("Top households (hhid) by distinct session count", hhid_counter, args.top)
    print_top("Device models", device_model_counter, args.top)
    print_top("OS name", os_name_counter, args.top)
    print_top("OS versions", os_version_counter, args.top)
    print_top("Chrome versions", chrome_version_counter, args.top)
    print_top("WebView flag (True = embedded 'wv' UA)", webview_counter, args.top)
    print_top("Distinct Shaka error messages", shaka_message_counter, args.top)
    print_top("Distinct player_phase values", player_phase_counter, args.top)

    if args.full_tables:
        print_full_table("Device model vs. error (unique-session) count", "device_model", device_model_counter)
        print_full_table("HHID vs. unique-session count", "hhid", hhid_counter)

    LOGGER.info(
        "Completed parse_debug_user_agents raw_rows=%d distinct_sessions=%d",
        total_rows,
        len(rows),
    )


if __name__ == "__main__":
    main()
