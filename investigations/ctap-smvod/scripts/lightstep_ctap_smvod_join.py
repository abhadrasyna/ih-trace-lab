#!/usr/bin/env python3
"""
Lightstep CTAP <-> SM-VOD join script (Option A).

For a given date (DDMMYYYY), queries all SM-VOD SetupSession calls over that
full 24h UTC window, fetches the full trace for each match (which contains
BOTH the SM-VOD span and the CTAP root span), joins them, breaks the
User-Agent string into columns, and writes one CSV report.

Session-identity fields (from SM-VOD "SetupSession" span):
    householdId, deviceId, session.clientIp, sessionId, contentId,
    externalPackageId

User-Agent fields (from CTAP root span, route ==
"/ctap/:uxApiVersion/devices/me/playsessions"), broken into columns:
    Mozilla, Platform, Engine, Compat Note, Browser, Mobile, Compat Token

Derived / device-identification helper columns:
    OS Family, OS Version, Browser Name, Browser Version,
    Device Class (Mobile/Desktop/Tablet/Unknown), deviceType (ground truth
    tag from SM-VOD span), raw_user_agent

Requires: LIGHTSTEP_API_KEY env var (Lightstep -> Settings -> API Keys)

Usage:
    export LIGHTSTEP_API_KEY=xxxx
    python3 lightstep_ctap_smvod_join.py \
        --date 09072026 \
        --org Synamedia-EU \
        --project mcs-go-prod-iye9omdf-eu \
        --base-url https://api.eu.lightstep.com \
        --out ../output/setupsession_09072026.csv
"""
import argparse
from lib import csv_io_compat as csv
import datetime
import os
import re
import sys
import time
import requests

CTAP_ROUTE = "/ctap/:uxApiVersion/devices/me/playsessions"

# ---------------------------------------------------------------------------
# User-Agent parsing
# ---------------------------------------------------------------------------
# Generic desktop/mobile Chromium-style UA:
#   Mozilla/5.0 (<platform>) <engine> (<compat note>) <browser>[ Mobile] <compat token>
UA_RE = re.compile(
    r'^(?P<mozilla>Mozilla/[\d.]+)\s*'
    r'\((?P<platform>[^)]*)\)\s*'
    r'(?P<engine>\S+/[\d.]+)\s*'
    r'(?:\((?P<compat_note>[^)]*)\)\s*)?'
    r'(?P<rest>.*)$'
)

# Recognize the actual browser token among the trailing tokens (rest), and
# whether "Mobile" is present, and the final compat token (e.g. Safari/537.36)
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

    # Non-browser clients (internal http libs, native SDKs, etc.)
    if not ua.startswith("Mozilla/"):
        # e.g. "axios/1.13.5", "okhttp/4.9.0", "AVPlayer/1.0"
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

    # "Mobile" flag can appear as a standalone token ("Mobile") or with a
    # build id ("Mobile/15E148" on iOS Safari) -- \b boundary handles both.
    is_mobile = bool(re.search(r'\bMobile\b', rest))
    result["Mobile"] = "Mobile" if is_mobile else ""
    rest_wo_mobile = re.sub(r'\bMobile(/\S+)?\b', '', rest).strip()
    rest_tokens = rest_wo_mobile.split()

    # iOS/macOS Safari reports its *real* user-visible version in a separate
    # "Version/x.y" token; the trailing "Safari/x.y" is just the WebKit build
    # number and should NOT be treated as the browser version.
    version_token = next((t for t in rest_tokens if t.startswith("Version/")), None)

    # Identify actual browser (precedence: Edg > OPR > SamsungBrowser >
    # Chrome/CriOS > FxiOS/Firefox > Safari), and the compat token (usually
    # the final Safari/x.y.z token on Chromium/Safari browsers).
    browser_token = ""
    compat_token = ""
    for tok in rest_tokens:
        name = tok.split("/")[0]
        if name in BROWSER_TOKENS:
            if browser_token == "" or name in ("Edg", "OPR", "SamsungBrowser", "Chrome", "CriOS"):
                if name == "Safari" and browser_token:
                    compat_token = tok  # trailing Safari/x is compat noise if we already found the real browser
                else:
                    browser_token = tok
            else:
                compat_token = tok
    if not compat_token and rest_tokens and rest_tokens[-1] != browser_token:
        compat_token = rest_tokens[-1]

    # Safari-specific correction: if a Version/x.y token is present, that's
    # the true browser version; the Safari/x.y token becomes the compat/
    # engine-build token instead.
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

    # --- OS Family / Version from Platform string ---
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
# Lightstep API helpers
# ---------------------------------------------------------------------------
def api_get(base_url, path, api_key, params=None, max_retries=6):
    """GET with exponential backoff on 429 (rate limit)."""
    url = f"{base_url}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    delay = 1.5
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            print(f"  rate limited, backing off {delay:.1f}s (attempt {attempt + 1})", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            continue
        if not resp.ok:
            print(f"  HTTP {resp.status_code} error body: {resp.text[:1000]}", file=sys.stderr)
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Gave up after {max_retries} retries on {url}")


def query_setup_sessions(base_url, org, project, api_key, oldest, youngest):
    """Find all SM-VOD SetupSession span/trace ids in the time window."""
    path = f"/public/v0.2/{org}/projects/{project}/searches"
    params = {
        "query": 'api == "SetupSession" && `http.route` == "/streamingSession"',
        "oldest-time": oldest,
        "youngest-time": youngest,
    }
    data = api_get(base_url, path, api_key, params=params)
    series = data.get("data", {}).get("attributes", {}).get("series", [])
    matches = []
    for s in series:
        labels = dict(x.split("=", 1) for x in s["group-labels"])
        matches.append({
            "span_id": labels.get("lightstep.span_id"),
            "trace_id": labels.get("lightstep.trace_id"),
            "ts_ms": s["points"][0][0] if s.get("points") else None,
        })
    return matches


def fetch_trace(base_url, org, project, api_key, trace_id_hex, start_time_iso):
    path = f"/public/v0.2/{org}/projects/{project}/traces"
    params = {"trace-id": trace_id_hex, "start-time": start_time_iso}
    return api_get(base_url, path, api_key, params=params)


def extract_row(trace_json):
    spans = trace_json["data"][0]["attributes"]["spans"]
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
        "deviceType": smvod.get("deviceType"),  # ground-truth tag, useful cross-check vs parsed UA
        "raw_user_agent": ctap_ua or "",
    }
    row.update(ua_cols)
    return row


def dec_to_hex(dec_str):
    return format(int(dec_str), "x")


FIELDS = [
    "householdId", "deviceId", "session.clientIp", "sessionId", "contentId",
    "externalPackageId", "deviceType",
    "Mozilla", "Platform", "Engine", "Compat Note", "Browser", "Mobile", "Compat Token",
    "OS Family", "OS Version", "Browser Name", "Browser Version", "Device Class",
    "raw_user_agent",
]


def ddmmyyyy_to_window(date_str):
    """Convert DDMMYYYY -> (oldest_iso, youngest_iso) covering full 24h UTC."""
    d = datetime.datetime.strptime(date_str, "%d%m%Y").replace(tzinfo=datetime.timezone.utc)
    oldest = d.strftime("%Y-%m-%dT%H:%M:%SZ")
    youngest = (d + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return oldest, youngest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 09072026. Queries full 24h UTC.")
    ap.add_argument("--org", required=True, help="Lightstep organization, e.g. Synamedia-EU")
    ap.add_argument("--project", required=True, help="Lightstep project id, e.g. mcs-go-prod-iye9omdf-eu")
    ap.add_argument("--base-url", default="https://api.eu.lightstep.com",
                     help="Use https://api.lightstep.com for US projects")
    ap.add_argument("--out", default=None, help="Output CSV path (default: ../output/setupsession_<date>.csv)")
    ap.add_argument("--rate-limit-sleep", type=float, default=1.0,
                     help="Seconds to sleep between trace fetches")
    args = ap.parse_args()

    api_key = os.environ.get("LIGHTSTEP_API_KEY")
    if not api_key:
        print("ERROR: set LIGHTSTEP_API_KEY env var", file=sys.stderr)
        sys.exit(1)

    oldest, youngest = ddmmyyyy_to_window(args.date)
    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "output", f"setupsession_{args.date}.csv"
    )

    print(f"Querying SetupSession spans {oldest} -> {youngest} ...")
    matches = query_setup_sessions(args.base_url, args.org, args.project, api_key, oldest, youngest)
    print(f"Found {len(matches)} SetupSession calls")

    rows = []
    for i, m in enumerate(matches, 1):
        trace_hex = dec_to_hex(m["trace_id"])
        start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(m["ts_ms"] / 1000))
        try:
            trace_json = fetch_trace(args.base_url, args.org, args.project, api_key, trace_hex, start_iso)
            row = extract_row(trace_json)
            if row:
                rows.append(row)
                print(f"  [{i}/{len(matches)}] ok  trace={trace_hex}")
            else:
                print(f"  [{i}/{len(matches)}] no SetupSession span found in trace={trace_hex}")
        except Exception as e:
            print(f"  [{i}/{len(matches)}] FAILED trace={trace_hex}: {e}", file=sys.stderr)
        time.sleep(args.rate_limit_sleep)  # be gentle -- avoid 429s

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
