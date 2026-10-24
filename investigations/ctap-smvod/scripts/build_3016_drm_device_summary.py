"""Per-device-model summary of 3014/3015/3016 events that carry DRM columns (pure logic, no file I/O)."""
from __future__ import annotations

SUMMARY_COLUMNS = [
    "opco", "subcategory", "cdm_make", "cdm_model", "security_level", "events", "households", "license_ok",
]


def _license_ok(status: str) -> bool:
    return status.startswith("2")


def summarise(events: list[dict]) -> list[dict]:
    """Group events by (opco, subcategory, make, model, security level), largest groups first.

    ``households`` counts distinct non-empty ``household_id``; ``license_ok`` counts events whose
    ``license_status`` is 2xx. Events without a CDM row group under empty make/model.
    """
    groups: dict[tuple[str, str, str, str, str], dict] = {}
    for e in events:
        key = (e["opco"], e["subcategory"], e["cdm_make"], e["cdm_model"], e["security_level"])
        g = groups.setdefault(key, {"events": 0, "households": set(), "license_ok": 0})
        g["events"] += 1
        if e["household_id"]:
            g["households"].add(e["household_id"])
        if _license_ok(e["license_status"]):
            g["license_ok"] += 1
    rows = [
        dict(zip(SUMMARY_COLUMNS[:5], key), events=g["events"], households=len(g["households"]),
             license_ok=g["license_ok"])
        for key, g in groups.items()
    ]
    return sorted(rows, key=lambda r: (r["opco"], r["subcategory"], -r["events"], r["cdm_make"], r["cdm_model"]))
