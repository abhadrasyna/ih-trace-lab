"""Build per-event rows for the 3014/3015/3016 sub-category report (pure logic, no file or network I/O)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from classify_3016_subcategory import classify

SEGMENT_RE = re.compile(r"/vod[ec]/([0-9a-f-]{36})/(\d+)/([^/?\s]+)")
MODEL_RE = re.compile(r"Android [\d.]+; ([^;)]+?)(?: Build/[^;)]*)?(?:; wv)?\)")
BROWSERS = (
    (r"Edge?A?/(\d+)", "Edge"),
    (r"OPR/(\d+)", "Opera"),
    (r"(?:Firefox|FxiOS)/(\d+)", "Firefox"),
    (r"SamsungBrowser/(\d+)", "Samsung Internet"),
    (r"(?:Chrome|CriOS)/(\d+)", "Chrome"),
    (r"Version/([\d.]+).*Safari", "Safari"),
)


def parse_segment(text: str) -> tuple[str, str]:
    """Return (content_uuid, segment_file) from a vode/vodc segment URL, else empty strings."""
    m = SEGMENT_RE.search(text or "")
    return (m.group(1), m.group(3)) if m else ("", "")


def parse_device_model(ua: str) -> str:
    m = MODEL_RE.search(ua)
    if m:
        return m.group(1).strip()
    if re.search(r"iPhone|iPad|Macintosh", ua):
        return "iOS/Mac"
    if "Android" in ua:
        return "android (model unknown)"
    return "desktop/other" if re.search(r"Windows|Linux|CrOS", ua) else "unknown"


def parse_browser(ua: str) -> str:
    for pattern, name in BROWSERS:
        m = re.search(pattern, ua)
        if m:
            return f"{name} {m.group(1)}"
    return "unknown"


def _event_row(e: dict, s: dict, p: dict, opco: str, date: str) -> dict:
    ua = e.get("user_agent") or ""
    seg_uuid, seg_file = parse_segment(e.get("pipeline_status", ""))
    return {
        "date": date,
        "opco": opco,
        "subcategory": classify(e),
        "errorcode": e["errorcode"],
        "datetime": e["datetime"],
        "householdId": e["householdId"],
        "deviceId": e["deviceId"],
        "sessionId": e["sessionId"],
        "content_uuid": s.get("content_uuid") or p.get("content_uuid") or seg_uuid,
        "externalPackageId": s.get("externalPackageId", ""),
        "segment_file": seg_file,
        "event_position": e.get("position", ""),
        "player_phase": e.get("player_phase", ""),
        "pipeline_status": e.get("pipeline_status", ""),
        "browser": parse_browser(ua),
        "device_model": parse_device_model(ua),
        "os": f'{s.get("OS Family", "")} {s.get("OS Version", "")}'.strip(),
        "user_agent": ua,
        "session_max_position": p.get("max_position", ""),
        "join_setup": bool(s),
        "join_position": bool(p),
    }


def build_events(errors: list[dict], setup: dict, pos: dict, opco: str, date: str) -> list[dict]:
    """One row per error; `setup`/`pos` map sessionId to the first row of that session."""
    rows = []
    for e in errors:
        sid = e["sessionId"]
        s, p = (setup.get(sid, {}), pos.get(sid, {})) if sid else ({}, {})
        rows.append(_event_row(e, s, p, opco, date))
    hh_events = Counter((r["subcategory"], r["householdId"]) for r in rows if r["householdId"])
    content_hh: dict[tuple, set] = defaultdict(set)
    for r in rows:
        if r["householdId"] and r["content_uuid"]:
            content_hh[(r["subcategory"], r["content_uuid"])].add(r["householdId"])
    for r in rows:
        r["hh_repeat_events"] = hh_events.get((r["subcategory"], r["householdId"]), 0)
        r["content_distinct_hh"] = len(content_hh.get((r["subcategory"], r["content_uuid"]), ()))
    return rows
