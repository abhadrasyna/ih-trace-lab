#!/usr/bin/env python3
"""Device breakdown of one error code in the flattened GH error eventdata (counts only, no ids printed).

Same device fields as ``webview_device_summary_report`` (model, Android version, build id, parsed from the
user agent), but over all error events and split by ``is_wv``. One row per (is_wv, model, android, build):
deduped events (messageid), distinct sessions, devices and households. Events whose user agent has no
Android build segment (iOS, desktop, TV) are reported once as "(unparsed)" with their UA family, never dropped.

Usage:
    python scripts/summarize_error_devices.py --code 3016 --input-dir data/reference/GH [--with-build]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mec_lib.error_events import dedupe_events, find_files, read_events, select_files  # noqa: E402
from mec_lib.ua_device import parse_device, ua_family  # noqa: E402
from src.lib.logging.bootstrap import init_logging  # noqa: E402


def device_key(row: dict[str, str], with_build: bool) -> tuple[str, str, str, str]:
    """``(is_wv, model, android_version, build_or_family)`` for one event; unparsed UAs keep their OS family."""
    model, android, build = parse_device(row.get("user_agent", ""))
    wv = (row.get("is_wv") or "").strip().lower() or "(blank)"
    if not model:
        return wv, "(unparsed)", ua_family(row.get("user_agent", "")), ""
    return wv, model, android, build if with_build else ""


def summarize_devices(rows: list[dict[str, str]], with_build: bool = False) -> list[dict]:
    """Group deduped events by device key; sorted by events then key so output is stable."""
    groups: dict[tuple, dict[str, set]] = defaultdict(lambda: {"events": set(), "sessions": set(), "devices": set(), "households": set()})
    for row in rows:
        group = groups[device_key(row, with_build)]
        group["events"].add(row["messageid"])
        for field, column in (("sessions", "sessionId"), ("devices", "deviceId"), ("households", "householdId")):
            value = (row.get(column) or "").strip()
            if value:
                group[field].add(value)
    out = [
        {"is_wv": k[0], "device_model": k[1], "android_or_family": k[2], "build_id": k[3],
         **{field: len(values) for field, values in g.items()}}
        for k, g in groups.items()
    ]
    return sorted(out, key=lambda r: (-r["events"], r["device_model"], r["android_or_family"], r["build_id"]))


def render_summary(date: str, summary: list[dict], with_build: bool, top: int) -> str:
    """Plain-text table for one day, limited to the top rows."""
    total = sum(r["events"] for r in summary)
    unparsed = sum(r["events"] for r in summary if r["device_model"] == "(unparsed)")
    lines = [f"## {date}: {total} events, {len(summary)} device groups, unparsed {unparsed} ({unparsed * 100 / total:.0f}%)" if total else f"## {date}: no events"]
    for r in summary[:top]:
        build = f" build={r['build_id']}" if with_build and r["build_id"] else ""
        lines.append(
            f"- wv={r['is_wv']} {r['device_model']} / {r['android_or_family']}{build}: events {r['events']}, "
            f"sessions {r['sessions']}, devices {r['devices']}, households {r['households']}"
        )
    if len(summary) > top:
        lines.append(f"- ... {len(summary) - top} more groups")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code", required=True, help="error code in the file name, for example 3016 or E31012")
    parser.add_argument("--input-dir", required=True, type=Path, help="folder with <date>_<code>.csv files")
    parser.add_argument("--dates", nargs="*", help="restrict to these YYYY-MM-DD dates")
    parser.add_argument("--with-build", action="store_true", help="split groups by Android build id")
    parser.add_argument("--top", type=int, default=15, help="rows shown per day")
    args = parser.parse_args()
    init_logging("mec-summarize_error_devices", to_file=False)

    for date, path in select_files(find_files(args.input_dir, args.code), args.dates):
        _, raw = read_events(path)
        print(render_summary(date, summarize_devices(dedupe_events(raw), args.with_build), args.with_build, args.top) + "\n")


if __name__ == "__main__":
    main()
