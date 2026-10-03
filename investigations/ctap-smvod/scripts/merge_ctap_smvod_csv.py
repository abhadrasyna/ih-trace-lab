#!/usr/bin/env python3
"""
3-way merge of Lightstep CSV exports:
    1. CTAP           (http.user_agent, lightstep.trace_id)
    2. SM-VOD aggregate (householdId, deviceId, session.clientIp, sessionId,
                          contentId, externalPackageId, lightstep.trace_id)
    3. SM-VOD span-samples (sessionId, oldest_micros, youngest_micros,
                             duration_millis, error_flag, span_name, ...)

Input file naming convention (in --input-dir, default ../data/lightstep):
    YYYY-MM-DD_ctap.csv      -- CTAP aggregate export
    YYYY-MM-DD_smvod.csv     -- SM-VOD aggregate export
    YYYY-MM-DD_smvod-ts.csv  -- SM-VOD span-samples export (has real timestamps
                                but no lightstep.trace_id; bridged via sessionId)

All files may contain extra Lightstep chart-aggregation columns
(min, max, avg, sum, value) -- these are dropped automatically. Extra columns
in smvod_ts (householdId, deviceId, contentId, externalPackageId,
session.clientIp, component_name, lightstep.trace_id) are also ignored since
they're redundant with file #2 or empty.

Join chain:
    csv1 (CTAP) <-> csv2 (SM-VOD aggregate) on `lightstep.trace_id`
    csv2 (SM-VOD aggregate) <-> csv3 (SM-VOD span-samples) on `sessionId`

Join type: FULL OUTER at each step so unmatched rows are kept with blank
columns + a `match_status` flag, making data gaps visible instead of silently
dropped.

Output: one CSV with session-identity columns, real timestamps/duration from
the span-samples export, the User-Agent broken into columns (Mozilla,
Platform, Engine, Compat Note, Browser, Mobile, Compat Token) plus derived
device-identification columns (OS Family, OS Version, Browser Name, Browser
Version, Device Class), the raw UA, trace_id, sessionId, content_uuid
(parsed from the SM-VOD aggregate's `session.playbackURL`/`playbackURL`
column when present -- the CDN's `vode/<uuid>/` segment, see
docs/STATUS.md 17 Jul 2026 "RESOLVED" entry -- blank for exports that
predate that column), and match_status.

Usage:
    python3 merge_ctap_smvod_csv.py --date 08072026
    python3 merge_ctap_smvod_csv.py --date 08072026 \
        --input-dir ../data/lightstep --out ../output/2026-07-08_setupsession.csv
"""
import argparse
from lib import csv_io_compat as csv
import datetime
import os
import re
import sys

from lib.runtime import snapshot_output_path

TRACE_KEY = "lightstep.trace_id"
SESSION_KEY = "sessionId"
# Same pattern as scripts/correlate_cdn_ips.py's extract_content_uuid() --
# the SM-VOD streamingSession span's playbackURL carries the CDN's
# vode/<uuid>/ (or vodc/<uuid>/ -- DRM-encrypted "vode" vs clear "vodc"
# delivery path, both seen in real exports, e.g. session
# abr-vod-a1082ec1-03d5-4c79-abec-721e7917a292 on 14072026 used
# dash-clear/vodc/...) content-UUID directly (see docs/STATUS.md, 17 Jul
# 2026 "RESOLVED" entry). Column is optional/new -- older
# SM-VOD aggregate exports won't have it, in which case content_uuid is
# just left blank.
CONTENT_UUID_RE = re.compile(r'/vod[a-z]/([a-f0-9-]+)/')
PLAYBACK_URL_KEYS = ("session.playbackURL", "playbackURL")


def extract_content_uuid(url):
    if not url:
        return ""
    m = CONTENT_UUID_RE.search(url)
    return m.group(1) if m else ""
IGNORE_COLS = {"min", "max", "avg", "sum", "value"}
# Columns from smvod_ts (span-samples) that duplicate the aggregate file or
# are unusable (trace_id is always empty in span-samples exports) -- ignored.
TS_IGNORE_COLS = {
    "householdId", "deviceId", "contentId", "externalPackageId",
    "session.clientIp", "component_name", TRACE_KEY,
}
TS_FIELDS = ["span_name", "error_flag", "oldest_micros", "youngest_micros", "duration_millis"]

# ---------------------------------------------------------------------------
# User-Agent parsing (same logic as process_traces.py)
# ---------------------------------------------------------------------------
UA_RE = re.compile(
    r'^(?P<mozilla>Mozilla/[\d.]+)\s*'
    r'\((?P<platform>[^)]*)\)\s*'
    r'(?P<engine>\S+/[\d.]+)\s*'
    r'(?:\((?P<compat_note>[^)]*)\)\s*)?'
    r'(?P<rest>.*)$'
)
BROWSER_TOKENS = ["Edg", "OPR", "SamsungBrowser", "Chrome", "CriOS", "FxiOS", "Firefox", "Safari"]

UA_COLUMNS = [
    "Mozilla", "Platform", "Engine", "Compat Note", "Browser", "Mobile", "Compat Token",
    "OS Family", "OS Version", "Browser Name", "Browser Version", "Device Class",
]


def parse_user_agent(ua):
    result = {c: "" for c in UA_COLUMNS}
    result["OS Family"] = "Unknown"
    result["Browser Name"] = "Unknown"
    result["Device Class"] = "Unknown"

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
# CSV loading / merging
# ---------------------------------------------------------------------------
def load_csv(path, extra_ignore_cols=frozenset()):
    """Load a Lightstep CSV export, dropping chart-aggregation columns.
    utf-8-sig strips a BOM if present, so `lightstep.trace_id` parses cleanly."""
    drop_cols = IGNORE_COLS | extra_ignore_cols
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            cleaned = {k: v for k, v in row.items() if k not in drop_cols}
            rows.append(cleaned)
        return rows


def micros_to_iso(micros_str):
    """Convert Lightstep epoch-microsecond string to an ISO-8601 UTC timestamp."""
    if not micros_str:
        return ""
    try:
        micros = int(micros_str)
    except ValueError:
        return ""
    dt = datetime.datetime.fromtimestamp(micros / 1_000_000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"


def _iso_date_str(date_ddmmyyyy):
    return datetime.datetime.strptime(date_ddmmyyyy, "%d%m%Y").strftime("%Y-%m-%d")


def find_input_file(input_dir, artifact, date, required=True):
    path = os.path.join(input_dir, f"{_iso_date_str(date)}_{artifact}.csv")
    if not os.path.exists(path):
        if required:
            print(f"ERROR: missing expected file {path}", file=sys.stderr)
            sys.exit(1)
        print(f"NOTE: missing optional file {path} -- timestamps will be blank", file=sys.stderr)
        return []
    return [path]


SMVOD_FIELDS = ["householdId", "deviceId", "session.clientIp", "sessionId",
                "contentId", "externalPackageId"]

TS_OUTPUT_FIELDS = ["span_name", "error_flag", "start_time", "end_time", "duration_millis"]

OUTPUT_FIELDS = (
    SMVOD_FIELDS + TS_OUTPUT_FIELDS + UA_COLUMNS +
    ["raw_user_agent", TRACE_KEY, "content_uuid", "match_status"]
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 08072026")
    ap.add_argument("--input-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "lightstep"))
    ap.add_argument("--out", default=None, help="Output CSV path (default: ../output/YYYY-MM-DD_setupsession.csv)")
    args = ap.parse_args()

    ctap_files = find_input_file(args.input_dir, "ctap", args.date)
    smvod_files = find_input_file(args.input_dir, "smvod", args.date)
    smvod_ts_files = find_input_file(args.input_dir, "smvod-ts", args.date, required=False)

    ctap_rows = []
    for f in ctap_files:
        ctap_rows.extend(load_csv(f))
    smvod_rows = []
    for f in smvod_files:
        smvod_rows.extend(load_csv(f))
    smvod_ts_rows = []
    for f in smvod_ts_files:
        smvod_ts_rows.extend(load_csv(f, extra_ignore_cols=TS_IGNORE_COLS))

    ctap_by_trace = {r[TRACE_KEY]: r for r in ctap_rows if r.get(TRACE_KEY)}
    smvod_by_trace = {r[TRACE_KEY]: r for r in smvod_rows if r.get(TRACE_KEY)}
    # sessionId is the bridge key into the span-samples (timestamp) export,
    # since that export never carries lightstep.trace_id.
    ts_by_session = {r[SESSION_KEY]: r for r in smvod_ts_rows if r.get(SESSION_KEY)}

    all_trace_ids = set(ctap_by_trace) | set(smvod_by_trace)

    out_rows = []
    matched = 0
    smvod_only = 0
    ctap_only = 0
    ts_matched = 0
    ts_missing = 0

    for tid in all_trace_ids:
        smvod_row = smvod_by_trace.get(tid)
        ctap_row = ctap_by_trace.get(tid)

        if smvod_row and ctap_row:
            status = "matched"
            matched += 1
        elif smvod_row and not ctap_row:
            status = "smvod_only (no CTAP UA found for this trace)"
            smvod_only += 1
        else:
            status = "ctap_only (no SM-VOD session data found for this trace)"
            ctap_only += 1

        row = {}
        for field in SMVOD_FIELDS:
            row[field] = smvod_row.get(field, "") if smvod_row else ""

        playback_url = ""
        if smvod_row:
            for key in PLAYBACK_URL_KEYS:
                if smvod_row.get(key):
                    playback_url = smvod_row[key]
                    break
        row["content_uuid"] = extract_content_uuid(playback_url)

        # Bring in real timestamps/duration via sessionId bridge (3rd CSV)
        session_id = smvod_row.get(SESSION_KEY, "") if smvod_row else ""
        ts_row = ts_by_session.get(session_id) if session_id else None
        if ts_row:
            row["span_name"] = ts_row.get("span_name", "")
            row["error_flag"] = ts_row.get("error_flag", "")
            row["start_time"] = micros_to_iso(ts_row.get("oldest_micros", ""))
            row["end_time"] = micros_to_iso(ts_row.get("youngest_micros", ""))
            row["duration_millis"] = ts_row.get("duration_millis", "")
            if smvod_row:
                ts_matched += 1
        else:
            for field in TS_OUTPUT_FIELDS:
                row[field] = ""
            if smvod_row:
                ts_missing += 1
            if status == "matched":
                status = "matched (no timestamp found for sessionId)"
            elif status.startswith("smvod_only"):
                status = "smvod_only (no CTAP UA, no timestamp found for sessionId)"

        ua = ctap_row.get("http.user_agent", "") if ctap_row else ""
        row.update(parse_user_agent(ua))
        row["raw_user_agent"] = ua
        row[TRACE_KEY] = tid
        row["match_status"] = status
        out_rows.append(row)

    # Sort chronologically when timestamps are available, matched-first otherwise
    def sort_key(r):
        status_rank = 0 if r["match_status"].startswith("matched") else (
            1 if r["match_status"].startswith("smvod_only") else 2)
        return (status_rank, r.get("start_time") or "9999")
    out_rows.sort(key=sort_key)

    out_path = args.out or snapshot_output_path(args.date, "setupsession")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"CTAP rows loaded:      {len(ctap_rows)}")
    print(f"SM-VOD rows loaded:    {len(smvod_rows)}")
    print(f"SM-VOD-ts rows loaded: {len(smvod_ts_rows)} (timestamp bridge via sessionId)")
    print(f"CTAP<->SM-VOD matched (trace_id):    {matched}")
    print(f"SM-VOD only (missing CTAP UA):       {smvod_only}")
    print(f"CTAP only (missing SM-VOD session):  {ctap_only}")
    print(f"Timestamp matched (via sessionId):   {ts_matched}")
    print(f"Timestamp missing (via sessionId):   {ts_missing}")
    print(f"\nWrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
