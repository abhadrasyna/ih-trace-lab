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
import re
from collections import Counter
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.parse_debug_user_agents")

# Matches the common embedded-Android-WebView UA shape, e.g.:
# "Mozilla/5.0 (Linux; Android 14; SM-A047F Build/UP1A.231005.007; wv) ...
#  Chrome/148.0.7778.217 Mobile Safari/537.36"
ANDROID_VERSION_RE = re.compile(r"Android\s+([\d.]+)")
DEVICE_MODEL_RE = re.compile(r"Android\s+[\d.]+;\s*([^;]+?)\s+Build/")
# Fallback for Chrome's User-Agent Reduction shape, which drops "Build/"
# entirely and reduces the model to a bare token, e.g. "Android 10; K)".
DEVICE_MODEL_NO_BUILD_RE = re.compile(r"Android\s+[\d.]+;\s*([^;)]+?)\)")
BUILD_ID_RE = re.compile(r"Build/([^;)]+)")
CHROME_VERSION_RE = re.compile(r"Chrome/([\d.]+)")
WEBVIEW_RE = re.compile(r";\s*wv\)")

# Desktop / non-Android UA shapes (Chrome's "User-Agent Reduction" also
# replaces Android device models with a bare "K" placeholder -- handled
# as its own case below rather than as "unparsed").
WINDOWS_RE = re.compile(r"Windows NT ([\d.]+)")
MACOS_RE = re.compile(r"Mac OS X ([\d_]+)")
IOS_RE = re.compile(r"(?:iPhone|iPad|iPod).*?CPU (?:iPhone )?OS ([\d_]+)")
LINUX_DESKTOP_RE = re.compile(r"X11; Linux")


def parse_user_agent(ua):
    """Extract os_name, os_version, device_model, build_id, chrome_version,
    and is_webview from a single user_agent string. Fields default to '' /
    False when the UA doesn't match any known shape, rather than raising.

    Handles, in order: embedded-Android-WebView devices (real model or the
    "K" UA-reduction placeholder), Windows/macOS/Linux desktop browsers,
    and iOS. Anything else falls back to os_name="Other"/empty fields."""
    if not ua:
        return {
            "os_name": "",
            "os_version": "",
            "device_model": "",
            "build_id": "",
            "chrome_version": "",
            "is_webview": False,
        }

    chrome_match = CHROME_VERSION_RE.search(ua)
    chrome_version = chrome_match.group(1) if chrome_match else ""

    android_match = ANDROID_VERSION_RE.search(ua)
    if android_match:
        device_match = DEVICE_MODEL_RE.search(ua)
        build_match = BUILD_ID_RE.search(ua)
        raw_model = device_match.group(1) if device_match else ""
        if not raw_model:
            fallback_match = DEVICE_MODEL_NO_BUILD_RE.search(ua)
            raw_model = fallback_match.group(1) if fallback_match else ""
        # Chrome's User-Agent Reduction masks the real model as "K" for
        # unrecognized/non-allow-listed devices -- label it distinctly
        # from a genuinely unparsed/unmatched UA.
        device_model = "K (device masked - UA reduction)" if raw_model == "K" else raw_model
        return {
            "os_name": "Android",
            "os_version": android_match.group(1),
            "device_model": device_model,
            "build_id": build_match.group(1) if build_match else "",
            "chrome_version": chrome_version,
            "is_webview": bool(WEBVIEW_RE.search(ua)),
        }

    windows_match = WINDOWS_RE.search(ua)
    if windows_match:
        return {
            "os_name": "Windows",
            "os_version": windows_match.group(1),
            "device_model": "Desktop (Windows)",
            "build_id": "",
            "chrome_version": chrome_version,
            "is_webview": False,
        }

    macos_match = MACOS_RE.search(ua)
    if macos_match:
        return {
            "os_name": "macOS",
            "os_version": macos_match.group(1).replace("_", "."),
            "device_model": "Desktop (macOS)",
            "build_id": "",
            "chrome_version": chrome_version,
            "is_webview": False,
        }

    ios_match = IOS_RE.search(ua)
    if ios_match:
        return {
            "os_name": "iOS",
            "os_version": ios_match.group(1).replace("_", "."),
            "device_model": "iPhone/iPad",
            "build_id": "",
            "chrome_version": chrome_version,
            "is_webview": False,
        }

    if LINUX_DESKTOP_RE.search(ua):
        return {
            "os_name": "Linux",
            "os_version": "",
            "device_model": "Desktop (Linux)",
            "build_id": "",
            "chrome_version": chrome_version,
            "is_webview": False,
        }

    return {
        "os_name": "Other/unparsed",
        "os_version": "",
        "device_model": "(unparsed)",
        "build_id": "",
        "chrome_version": chrome_version,
        "is_webview": False,
    }


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
