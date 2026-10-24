"""Summarise 3014/3015/3016 events per OpCo and sub-category (pure logic, no file or network I/O)."""
from __future__ import annotations

from classify_3016_subcategory import PRIORITY, UNCATEGORISED

SUMMARY_COLUMNS = ["date", "opco", "subcategory", "events", "households", "sessions", "priority"]


def build_summary(events: list[dict]) -> list[dict]:
    """One row per (opco, subcategory) that has events; households/sessions are distinct, non-empty ids."""
    dates = {e["date"] for e in events}
    if len(dates) > 1:
        raise ValueError(f"events span multiple dates {sorted(dates)}; summarise one day at a time")
    groups: dict[tuple[str, str], dict] = {}
    for e in events:
        key = (e["opco"], e["subcategory"])
        g = groups.setdefault(key, {"date": e["date"], "events": 0, "households": set(), "sessions": set()})
        g["events"] += 1
        if e.get("householdId"):
            g["households"].add(e["householdId"])
        if e.get("sessionId"):
            g["sessions"].add(e["sessionId"])
    return [
        {
            "date": g["date"],
            "opco": opco,
            "subcategory": sub,
            "events": g["events"],
            "households": len(g["households"]),
            "sessions": len(g["sessions"]),
            "priority": PRIORITY.get(sub, PRIORITY[UNCATEGORISED]),
        }
        for (opco, sub), g in sorted(groups.items())
    ]
