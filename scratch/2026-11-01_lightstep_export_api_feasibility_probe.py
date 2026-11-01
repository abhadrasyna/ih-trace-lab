"""Probe: reproduce hand-exported Lightstep daily CSVs via the public query_timeseries API (LX-1).

Usage: python3 scratch/2026-11-01_lightstep_export_api_feasibility_probe.py --kind ctap --tenant ZA \
    --start 2026-10-29T00:00:00Z --minutes 10 [--show-body]
Prints status, latency, series count, labels and a sample. Token comes from .env, never printed.
"""
import argparse
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASES = {"EU": ("https://api.eu.lightstep.com/public/v0.2", "Synamedia-EU", "LIGHTSTEP_API_KEY_EU"),
         "US": ("https://api.lightstep.com/public/v0.2", "Synamedia", "LIGHTSTEP_API_KEY_US")}

UQL = {
    "ctap": 'spans count | delta | filter http.route == "/ctap/:uxApiVersion/devices/me/playsessions" '
            '| group_by ["http.user_agent", "lightstep.trace_id"], sum',
    "smvod": 'spans count | delta | filter (service == "sm-linear" || service == "sm-vod") '
             '&& session.api == "SetupSession" && span.kind == "server" '
             '| group_by ["householdId","deviceId","session.clientIp","sessionId","contentId",'
             '"externalPackageId","lightstep.trace_id","playbackURL"], sum',
    "mdrmfe": 'spans count | delta | filter service == "go-mdrmfe" && request.tenant == "{goid}" && span.kind == "server" '
              '| group_by ["drmAuthToken.sessionId","fcid","drmAuthToken.householdId","drmAuthToken.deviceId",'
              '"drmAuthToken.deviceType","drmAuthToken.drmType","drmAuthToken.brRef","request.contentId",'
              '"http.status_code","http.user_agent","http.client_ip"], sum',
    "mdrm-cdm-widevine": 'spans count | delta | filter ("tenantId" == "{tid}") && ("service" == "widevine-license-generator") '
                         '&& (operation == "/wvpl/:version/GetLicense") | group_by ["fcId","http.status_code",'
                         '"drmInfo.DeviceType","drmInfo.Make","drmInfo.Model","drmInfo.Platform","drmInfo.SecurityLevel"], sum',
    "mdrm-cdm-fairplay": 'spans count | delta | filter ("tenantId" == "{tid}") && ("service" == "fairplay-license-generator") '
                         '&& (operation == "/MDRM/FPLS/:version/GetLicense") | group_by ["fcId","http.status_code","FP_SPC_contents"], sum',
    "mdrm-cdm-playready": 'spans count | delta | filter ("tenantId" == "{tid}") && ("service" == "playready") '
                          '&& (operation == "/playready/rightsmanager.asmx") | group_by ["fcId","http.status_code",'
                          '"drmInfo.deviceType","drmInfo.manufacturerName","drmInfo.modelName"], sum',
    "mdrm-lrm": 'spans count | delta | filter ("tenantId" == "{tid}") && ("service" == "license-request-manager") '
                '| group_by ["fcId","deviceId","http.status_code"], sum',
}


def load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def resolve(system: str, tenant: str) -> dict:
    out = subprocess.run([sys.executable, "scripts/resolve_tenant.py", "--system", system, "--tenant", tenant],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def post(region: str, project: str, body: dict) -> tuple[int, dict | str, float]:
    base, org, env = BASES[region]
    req = urllib.request.Request(f"{base}/{org}/projects/{project}/telemetry/query_timeseries",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"bearer {os.environ[env]}",
                                          "Content-Type": "application/json", "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read()), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500], time.time() - t0
    except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError):
        return 599, "network", time.time() - t0


def build_body(query: str, start: datetime, end: datetime, period: int) -> dict:
    return {"data": {"attributes": {
        "query": query, "query-type": "default",
        "oldest-time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "youngest-time": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output-period": period, "include-exemplars": False}}}


def fetch(ctx: dict, query: str, start: datetime, end: datetime, stats: dict) -> dict:
    """Series keyed by group-labels tuple; halves any window that returns >= 50 series."""
    status, resp, dt = post(ctx["region"], ctx["project"], build_body(query, start, end, int((end - start).total_seconds())))
    stats["calls"] += 1
    stats["lat"].append(dt)
    if status == 429 or status >= 500:
        stats["errors"].append(status)
        if len(stats["errors"]) > 20:
            raise SystemExit(f"too many retryable errors: {stats['errors']}")
        time.sleep(5)
        return fetch(ctx, query, start, end, stats)
    if status != 200:
        raise SystemExit(f"HTTP {status}: {resp}")
    series = resp["data"]["attributes"].get("series", [])
    if len(series) >= 50 and (end - start).total_seconds() <= 1:
        raise SystemExit(f"still >= 50 series in a 1 s window at {start}; results would be truncated")
    if len(series) >= 50 and (end - start).total_seconds() > 1:
        mid = start + (end - start) / 2
        out = fetch(ctx, query, start, mid, stats)
        out.update({k: v for k, v in fetch(ctx, query, mid, end, stats).items() if k not in out})
        return out
    stats["maxfit"] = max(stats["maxfit"], (end - start).total_seconds())
    return {tuple(s_["group-labels"]): s_["points"] for s_ in series}


def hand_keys(kind: str, tenant: str, date: str) -> set:
    import csv
    base = ROOT / f"investigations/ctap-smvod/data/lightstep/{tenant}"
    paths = [base / f"{date}_{kind}.csv"] if (base / f"{date}_{kind}.csv").exists() else sorted(base.glob(f"{date}_[0-9][0-9]_{kind}.csv"))
    keys: set = set()
    if not paths:
        raise SystemExit(f"no hand CSV for {kind} {tenant} {date}")
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            r = csv.DictReader(fh)
            skip = {"min", "max", "avg", "sum", "value"}
            cols = [c for c in r.fieldnames if c not in skip]
            keys |= {tuple(f"{c}={row[c]}" for c in cols) for row in r}
    return keys


def run_day(a, ctx, query) -> None:
    day = datetime.strptime(a.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    stats = {"calls": 0, "lat": [], "errors": [], "maxfit": 0}
    got: dict = {}
    if a.hours < 1 or 24 % a.hours:
        raise SystemExit("--hours must be a divisor of 24")
    for h in range(0, 24, a.hours):
        got.update(fetch(ctx, query, day + timedelta(hours=h), day + timedelta(hours=h + a.hours), stats))
    api = set(got)
    hand = hand_keys(a.kind, a.tenant, a.date)
    print(f"{a.kind}: api={len(api)} hand={len(hand)} both={len(api & hand)} only_api={len(api - hand)} only_hand={len(hand - api)}")
    lat = sorted(stats["lat"])
    print(f"calls={stats['calls']} p50={lat[len(lat)//2]:.1f}s max={lat[-1]:.1f}s errors={stats['errors']} "
          f"largest_untruncated_window_s={stats['maxfit']:.0f}")
    for k in list(api - hand)[:2]:
        print("  only_api sample:", k[:4])
    for k in list(hand - api)[:2]:
        print("  only_hand sample:", k[:4])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=sorted(UQL))
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--start", default="2026-10-29T00:00:00Z")
    ap.add_argument("--minutes", type=int, default=10)
    ap.add_argument("--period", type=int, default=0, help="output period seconds; 0 = whole window")
    ap.add_argument("--show-body", action="store_true")
    ap.add_argument("--date", help="UTC day YYYY-MM-DD: full-day sliced run compared with the hand CSV")
    ap.add_argument("--hours", type=int, default=1, help="initial slice size for --date")
    a = ap.parse_args()
    load_env()
    start = datetime.strptime(a.start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=a.minutes)
    system = "lightstep_mdrm" if a.kind.startswith("mdrm-") else "lightstep_go"
    ctx = resolve(system, a.tenant)
    tid = (ctx.get("filter") or {}).get("tenantId", "")
    if system == "lightstep_mdrm" and not tid:
        raise SystemExit(f"no mDRM tenantId for {a.tenant}")
    query = UQL[a.kind].replace("{tid}", tid).replace("{goid}", ctx["project"].split("-")[3] if a.kind == "mdrmfe" else "")
    body = build_body(query, start, end, a.period or a.minutes * 60)
    if a.date:
        return run_day(a, ctx, query)
    if a.show_body:
        print(json.dumps(body, indent=1))
    status, resp, dt = post(ctx["region"], ctx["project"], body)
    print(f"HTTP {status} in {dt:.1f}s")
    if status != 200:
        print(resp)
        return
    attrs = resp["data"]["attributes"]
    series = attrs.get("series", [])
    print("keys:", list(attrs), "series:", len(series))
    if series:
        print("sample:", json.dumps(series[0])[:500])


if __name__ == "__main__":
    main()
