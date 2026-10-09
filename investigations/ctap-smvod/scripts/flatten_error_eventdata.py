#!/usr/bin/env python3
"""Flatten raw PLAYER_ERROR debug-event rows into one analysis-ready CSV.

Input: one or more Athena exports of `<id>_ccl_debug_events` PLAYER_ERROR rows (columns: datetime,
messageid, clibversion, clientid, eventclass, eventid, eventdata). Output: one row per unique
`messageid` with the `eventdata` JSON split into columns (error code/text, shaka error, nested
DRM/HTTP error, player state, network details, user agent, is_wv) plus the untouched
`raw_eventdata`. A row whose eventdata is not valid JSON aborts the run.

Usage:
    python3 flatten_error_eventdata.py --input ../data/athena/ZM/errors_3016.csv ../data/athena/ZM/errors_1003.csv \
        --out ../output/ZM/2026-10-04_error_eventdata_flat.csv
"""
import argparse
import json
import logging
import re
from urllib.parse import urlparse

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.debug_event_parser import split_clientid
from lib.webview import is_wv_cell
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.flatten_error_eventdata")

FIELDS = [
    "datetime", "messageid", "clibversion", "deviceId", "householdId", "sessionId", "errorcode", "error_text",
    "position", "user_agent", "is_wv", "app_version",
    "shaka_code", "shaka_category", "shaka_message", "shaka_url", "shaka_url_host", "shaka_http_status",
    "nested_shaka_code", "nested_http_status", "nested_title", "nested_detail", "nested_mdrm_code",
    "player_phase", "player_readystate", "player_isbuffering", "player_ispaused", "player_isseeking",
    "net_type", "net_effectivetype", "net_downlink", "net_rtt",
    "stream_mbps", "est_bandwidth_mbps", "bytes_downloaded", "load_latency_s", "buffering_time_s", "drm_present",
    "raw_eventdata",
]
INPUT_COLUMNS = ("datetime", "messageid", "clientid", "eventdata")
_MDRM_CODE = re.compile(r'code\W+(\d{4,})')


def _get(obj: dict | None, *path: str):
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _first_url(data: list) -> str:
    return next((d for d in data if isinstance(d, str) and d.startswith("http")), "")


def _http_status(data: list):
    return next((d for d in data[1:2] if isinstance(d, int) and d >= 100), None)


def _nested(shaka: dict) -> dict:
    """The 6007-style wrapper carries the underlying shaka error as the first element of `data`."""
    data = shaka.get("data") or []
    inner = data[0] if data and isinstance(data[0], dict) else {}
    inner_data = inner.get("data") or []
    body = next((d for d in inner_data if isinstance(d, str) and d.startswith("{")), "")
    parsed = {}
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        LOGGER.warning("nested error body is not valid JSON; nested_* columns left blank: %.80s", body)
        parsed = {}
    mdrm = _MDRM_CODE.findall(parsed.get("detail", "")) if isinstance(parsed, dict) else []
    return {
        "nested_shaka_code": inner.get("code"),
        "nested_http_status": _http_status(inner_data),
        "nested_title": parsed.get("title", "") if isinstance(parsed, dict) else "",
        "nested_detail": parsed.get("detail", "") if isinstance(parsed, dict) else "",
        "nested_mdrm_code": mdrm[-1] if mdrm else "",
        "inner_url": _first_url(inner_data),
    }


def flatten_row(row: dict[str, str]) -> dict:
    """Pure: one export row -> one flat row. Raises ValueError on unparseable eventdata."""
    try:
        payload = json.loads(row["eventdata"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"messageid={row.get('messageid')}: eventdata is not valid JSON") from exc
    raw_desc = payload.get("errordescription")
    desc = raw_desc if isinstance(raw_desc, dict) else {"errordescription": raw_desc or ""}
    shaka = desc.get("shakaerror") or {}
    nested = _nested(shaka)
    url = _first_url(shaka.get("data") or []) or nested.pop("inner_url")
    nested.pop("inner_url", None)
    device_id, household_id = split_clientid(row.get("clientid", ""))
    ua = desc.get("user_agent", "")
    shaka_stats = _get(desc, "networkdetails", "shakastats")
    return {
        "datetime": row["datetime"], "messageid": row["messageid"], "clibversion": row.get("clibversion", ""),
        "deviceId": device_id, "householdId": household_id, "sessionId": payload.get("sessionid"),
        "errorcode": payload.get("errorcode"), "error_text": desc.get("errordescription", ""),
        "position": payload.get("position"), "user_agent": ua,
        "is_wv": is_wv_cell({"raw_user_agent": ua}), "app_version": desc.get("app_version"),
        "shaka_code": shaka.get("code"), "shaka_category": shaka.get("category"), "shaka_message": shaka.get("message"),
        "shaka_url": url, "shaka_url_host": urlparse(url).netloc,
        "shaka_http_status": _http_status(shaka.get("data") or []), **nested,
        "player_phase": _get(desc, "playerstatesnapshot", "phase"),
        "player_readystate": _get(desc, "playerstatesnapshot", "readystate"),
        "player_isbuffering": _get(desc, "playerstatesnapshot", "isbuffering"),
        "player_ispaused": _get(desc, "playerstatesnapshot", "ispaused"),
        "player_isseeking": _get(desc, "playerstatesnapshot", "isseeking"),
        "net_type": _get(desc, "networkdetails", "navigatorconnection", "type"),
        "net_effectivetype": _get(desc, "networkdetails", "navigatorconnection", "effectivetype"),
        "net_downlink": _get(desc, "networkdetails", "navigatorconnection", "downlink"),
        "net_rtt": _get(desc, "networkdetails", "navigatorconnection", "rtt"),
        "stream_mbps": _get(shaka_stats, "streambandwidthmbps"),
        "est_bandwidth_mbps": _get(shaka_stats, "estimatedbandwidthmbps"),
        "bytes_downloaded": _get(shaka_stats, "bytesdownloaded"),
        "load_latency_s": _get(shaka_stats, "loadlatency"),
        "buffering_time_s": _get(shaka_stats, "bufferingtime"),
        "drm_present": "true" if _get(desc, "networkdetails", "drmdiagnostics") else "false",
        "raw_eventdata": row["eventdata"],
    }


def flatten_rows(rows: list[dict[str, str]]) -> list[dict]:
    """Flatten and de-duplicate on messageid (first occurrence wins), sorted by datetime."""
    for row in rows:
        if not set(INPUT_COLUMNS) <= set(row):
            raise ValueError(f"input is missing required columns: {sorted(set(INPUT_COLUMNS) - set(row))}")
    seen: dict[str, dict] = {}
    for row in rows:
        seen.setdefault(row["messageid"], flatten_row(row))
    return sorted(seen.values(), key=lambda r: r["datetime"])


def read_rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    init_logging("ctap-smvod-flatten_error_eventdata")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", nargs="+", required=True, help="PLAYER_ERROR debug-event CSV export(s)")
    ap.add_argument("--out", required=True, help="Flattened output CSV path")
    args = ap.parse_args()

    rows = [r for path in args.input for r in read_rows(path)]
    flat = flatten_rows(rows)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(flat)
    LOGGER.info("Wrote %d unique error rows (from %d input rows) to %s", len(flat), len(rows), args.out)


if __name__ == "__main__":
    main()
