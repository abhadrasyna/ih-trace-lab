#!/usr/bin/env python3
"""
CTAP <-> SM-VOD trace join + report builder (local processing only).

This script does NOT call the Lightstep API itself -- it processes trace
JSON files that have already been fetched (e.g. via the Lightstep MCP tools
in a Copilot CLI session: query_spans to find matching SetupSession calls,
then get_stored_trace to pull each full trace).

Workflow:
    1. Copilot (or you, via the Lightstep UI/API) fetches each full trace for
       a given date and saves the raw JSON response as one file per trace in
       an input directory, e.g.:
           raw_traces/09072026/trace_0001.json
           raw_traces/09072026/trace_0002.json
           ...
    2. Run this script against that directory to produce the joined,
       UA-broken-down CSV report.

For each trace file, this script finds:
    - the SM-VOD "SetupSession" span -> householdId, deviceId,
      session.clientIp, sessionId, contentId, externalPackageId, deviceType
    - the CTAP root span (http.route ==
      "/ctap/:uxApiVersion/devices/me/playsessions") -> http.user_agent,
      broken into: Mozilla, Platform, Engine, Compat Note, Browser, Mobile,
      Compat Token, plus derived OS Family/Version, Browser Name/Version,
      Device Class -- useful for spotting device-specific issues.

Usage:
    python3 process_traces.py --input-dir raw_traces/09072026 \
                               --out ../output/setupsession_09072026.csv
"""
import argparse
from lib import csv_io_compat as csv
import glob
import json
import os
import re
import sys

CTAP_ROUTE = "/ctap/:uxApiVersion/devices/me/playsessions"

# ---------------------------------------------------------------------------
# User-Agent parsing
# ---------------------------------------------------------------------------
UA_RE = re.compile(
    r'^(?P<mozilla>Mozilla/[\d.]+)\s*'
    r'\((?P<platform>[^)]*)\)\s*'
    r'(?P<engine>\S+/[\d.]+)\s*'
    r'(?:\((?P<compat_note>[^)]*)\)\s*)?'
    r'(?P<rest>.*)$'
)

BROWSER_TOKENS = ["Edg", "OPR", "SamsungBrowser", "Chrome", "CriOS", "FxiOS", "Firefox", "Safari"]


def parse_user_agent(ua):
    """Return a dict with the UA broken into columns + derived fields.
    Falls back gracefully for non-browser UAs (e.g. axios/1.x, native apps)."""
    result = {
        "Mozilla": "", "Platform": "", "Engine": "", "Compat Note": "",
        "Browser": "", "Mobile": "", "Compat Token": "",
        "OS Family": "Unknown", "OS Version": "", "Browser Name": "Unknown",
        "Browser Version": "", "Device Class": "Unknown",
    }

    if not ua:
        return result

    if not ua.startswith("Mozilla/"):
        m = re.match(r'^([A-Za-z0-9_.\-]+)/([\d.]+)', ua)
        result["Browser Name"] = m.group(1) if m else ua.split("/")[0]
        result["Browser Version"] = m.group(2) if m else ""
        result["Device Class"] = "Internal/Client-Library"
        return result

    m = UA_RE.match(ua)
    if not m:
        result["Browser Name"] = "Unrecognized"
        return result

    result["Mozilla"] = m.group("mozilla").split("/")[-1]
    result["Platform"] = m.group("platform")
    result["Engine"] = m.group("engine")
    result["Compat Note"] = m.group("compat_note") or ""
    rest = m.group("rest").strip()

    is_mobile = bool(re.search(r'\bMobile\b', rest))
    result["Mobile"] = "Mobile" if is_mobile else ""
    rest_wo_mobile = re.sub(r'\bMobile(/\S+)?\b', '', rest).strip()
    rest_tokens = rest_wo_mobile.split()

    version_token = next((t for t in rest_tokens if t.startswith("Version/")), None)

    browser_token = ""
    compat_token = ""
    for tok in rest_tokens:
        name = tok.split("/")[0]
        if name in BROWSER_TOKENS:
            if browser_token == "" or name in ("Edg", "OPR", "SamsungBrowser", "Chrome", "CriOS"):
                if name == "Safari" and browser_token:
                    compat_token = tok
                else:
                    browser_token = tok
            else:
                compat_token = tok
    if not compat_token and rest_tokens and rest_tokens[-1] != browser_token:
        compat_token = rest_tokens[-1]

    if version_token and browser_token.startswith("Safari/"):
        compat_token = browser_token
        browser_token = f"Safari/{version_token.split('/', 1)[1]}"

    result["Browser"] = browser_token
    result["Compat Token"] = compat_token

    if browser_token:
        bname, _, bver = browser_token.partition("/")
        name_map = {"Edg": "Microsoft Edge", "OPR": "Opera", "CriOS": "Chrome (iOS)",
                    "FxiOS": "Firefox (iOS)", "SamsungBrowser": "Samsung Internet"}
        result["Browser Name"] = name_map.get(bname, bname)
        result["Browser Version"] = bver

    plat = result["Platform"]
    if "Android" in plat:
        result["OS Family"] = "Android"
        mv = re.search(r'Android ([\d.]+)', plat)
        result["OS Version"] = mv.group(1) if mv else ""
        result["Device Class"] = "Mobile" if is_mobile else "Tablet"
    elif "iPhone" in plat or "iPad" in plat:
        result["OS Family"] = "iOS" if "iPhone" in plat else "iPadOS"
        mv = re.search(r'OS ([\d_]+)', plat)
        result["OS Version"] = mv.group(1).replace("_", ".") if mv else ""
        result["Device Class"] = "Mobile" if "iPhone" in plat else "Tablet"
    elif "Mac OS X" in plat:
        result["OS Family"] = "macOS"
        mv = re.search(r'Mac OS X ([\d_]+)', plat)
        result["OS Version"] = mv.group(1).replace("_", ".") if mv else ""
        result["Device Class"] = "Desktop"
    elif "Windows" in plat:
        result["OS Family"] = "Windows"
        mv = re.search(r'Windows NT ([\d.]+)', plat)
        result["OS Version"] = mv.group(1) if mv else ""
        result["Device Class"] = "Desktop"
    elif "Linux" in plat:
        result["OS Family"] = "Linux"
        result["Device Class"] = "Desktop"
    elif "CrOS" in plat:
        result["OS Family"] = "ChromeOS"
        result["Device Class"] = "Desktop"

    return result


# ---------------------------------------------------------------------------
# Trace processing
# ---------------------------------------------------------------------------
def extract_row(trace_json, source_file=""):
    try:
        spans = trace_json["data"][0]["attributes"]["spans"]
    except (KeyError, IndexError, TypeError):
        print(f"  [{source_file}] unexpected trace JSON shape, skipping", file=sys.stderr)
        return None

    ctap_ua = None
    smvod = None
    for s in spans:
        t = s.get("tags", {})
        if t.get("http.route") == CTAP_ROUTE:
            ctap_ua = t.get("http.user_agent")
        if t.get("api") == "SetupSession":
            smvod = t

    if not smvod:
        return None

    ua_cols = parse_user_agent(ctap_ua)
    row = {
        "householdId": smvod.get("householdId"),
        "deviceId": smvod.get("deviceId"),
        "session.clientIp": smvod.get("session.clientIp"),
        "sessionId": smvod.get("sessionId"),
        "contentId": smvod.get("contentId"),
        "externalPackageId": smvod.get("externalPackageId"),
        "deviceType": smvod.get("deviceType"),
        "raw_user_agent": ctap_ua or "",
    }
    row.update(ua_cols)
    return row


FIELDS = [
    "householdId", "deviceId", "session.clientIp", "sessionId", "contentId",
    "externalPackageId", "deviceType",
    "Mozilla", "Platform", "Engine", "Compat Note", "Browser", "Mobile", "Compat Token",
    "OS Family", "OS Version", "Browser Name", "Browser Version", "Device Class",
    "raw_user_agent",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True,
                     help="Directory of raw trace JSON files (one per trace, as returned by "
                          "the Lightstep get_stored_trace MCP tool / API)")
    ap.add_argument("--glob", default="*.json", help="Filename glob within --input-dir")
    ap.add_argument("--out", required=True, help="Output CSV path")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, args.glob)))
    if not files:
        print(f"No files matched {args.input_dir}/{args.glob}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for f in files:
        try:
            trace_json = json.load(open(f))
        except Exception as e:
            print(f"  [{f}] failed to parse JSON: {e}", file=sys.stderr)
            continue
        row = extract_row(trace_json, source_file=f)
        if row:
            rows.append(row)
            print(f"  [{f}] ok")
        else:
            print(f"  [{f}] no SetupSession span found, skipped")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
