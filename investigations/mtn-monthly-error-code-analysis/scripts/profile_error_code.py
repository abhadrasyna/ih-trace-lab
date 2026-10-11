#!/usr/bin/env python3
"""Evidence profile of one error code in the flattened GH error eventdata (counts and shares only).

Per day: deduped events (messageid), distinct sessions, households and devices, sessions per household,
and the distribution of the classification evidence columns (error text, Shaka fields, MDRM wrapper,
timing signals, app and player versions, user-agent family). Ids are only counted, never printed. A column
missing from a day's file is reported as "(column absent)", which means never populated that day, not zero.
Per-event measurements (position values, *_bps, net_*) are not summed; position is bucketed 0 / >0.

Usage:
    python scripts/profile_error_code.py --code 3016 --input-dir data/reference/GH
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mec_lib.error_events import dedupe_events, distinct_count, find_files, read_events, select_files  # noqa: E402
from mec_lib.ua_device import ua_family  # noqa: E402
from src.lib.logging.bootstrap import init_logging  # noqa: E402

PROFILE_COLUMNS = (
    "errorcode", "error_text", "shaka_code", "shaka_category", "shaka_severity", "shaka_handled",
    "media_error_type", "pipeline_status", "nested_mdrm_code", "nested_mdrm_message",
    "is_wv", "app_version", "clibversion", "player_phase", "player_readystate",
)
MAX_VALUE_LEN = 120


def position_bucket(raw: str) -> str:
    """Bucket the per-event position: ``0`` (before playback), ``>0``, blank or non-numeric."""
    value = (raw or "").strip()
    if not value:
        return "(blank)"
    try:
        number = float(value)
    except ValueError:
        return "(non-numeric)"
    if not math.isfinite(number) or number < 0:
        return "(invalid)"
    return "0" if number == 0 else ">0"


def value_counts(rows: list[dict[str, str]], column: str) -> Counter:
    """Event count per distinct value; blanks are labelled ``(blank)``."""
    return Counter(((row.get(column) or "").strip() or "(blank)")[:MAX_VALUE_LEN] for row in rows)


def concentration(rows: list[dict[str, str]]) -> dict[str, float]:
    """Sessions per household (distinct sessions over distinct households); 0.0 when no household is present."""
    households = distinct_count(rows, "householdId")
    sessions = distinct_count(rows, "sessionId")
    return {"sessions_per_household": round(sessions / households, 2) if households else 0.0}


def build_profile(header: list[str], rows: list[dict[str, str]]) -> dict:
    """Profile one day's deduped events; ``columns`` maps column to counts, or ``None`` when absent."""
    columns: dict[str, Counter | None] = {}
    for column in PROFILE_COLUMNS:
        columns[column] = value_counts(rows, column) if column in header else None
    columns["ua_family"] = Counter(ua_family(row.get("user_agent", "")) for row in rows) if "user_agent" in header else None
    columns["position_bucket"] = Counter(position_bucket(row.get("position", "")) for row in rows) if "position" in header else None
    return {
        "events": len(rows),
        "sessions": distinct_count(rows, "sessionId"),
        "households": distinct_count(rows, "householdId"),
        "devices": distinct_count(rows, "deviceId"),
        **concentration(rows),
        "columns": columns,
    }


def render_profile(date: str, raw_rows: int, profile: dict) -> str:
    """Plain-text block for one day."""
    lines = [
        f"## {date}",
        f"raw rows {raw_rows}, events (messageid) {profile['events']}, sessions {profile['sessions']}, "
        f"households {profile['households']}, devices {profile['devices']}, "
        f"sessions/household {profile['sessions_per_household']}",
    ]
    total = profile["events"]
    for column, counts in profile["columns"].items():
        if counts is None:
            lines.append(f"- {column}: (column absent)")
            continue
        shown = ", ".join(f"{value!r} {n} ({n * 100 / total:.0f}%)" for value, n in counts.most_common(8))
        lines.append(f"- {column}: {shown}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code", required=True, help="error code in the file name, for example 3016 or E31012")
    parser.add_argument("--input-dir", required=True, type=Path, help="folder with <date>_<code>.csv files")
    parser.add_argument("--dates", nargs="*", help="restrict to these YYYY-MM-DD dates")
    args = parser.parse_args()
    init_logging("mec-profile_error_code", to_file=False)

    for date, path in select_files(find_files(args.input_dir, args.code), args.dates):
        header, raw = read_events(path)
        rows = dedupe_events(raw)
        if not rows:
            print(f"## {date}\nno rows")
            continue
        print(render_profile(date, len(raw), build_profile(header, rows)) + "\n")


if __name__ == "__main__":
    main()
