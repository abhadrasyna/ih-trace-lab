"""Shaka 6001 by Chrome/Android version and device-level cuts (SU-6).

Reads the SU-4 enriched CSV ``<start>_<end>_shaka6001_enriched.csv`` (base: 6001 events, one row per event,
UTC table timestamps, ``period`` already classified in IST) and writes under ``output/<tenant>/``:

* ``..._6001_by_chrome.csv`` / ``..._6001_by_android.csv`` -- events and distinct devices per version,
  before vs after, with each period's share of that period's events and the change in share;
* ``..._6001_drm_devices.csv`` + ``..._6001_drm_summary.csv`` -- impacted devices by ``drmenabled``. The story's
  ``drmenabled`` is the ``drmsupported`` key of the 6001 ``eventdata`` (SU-4 column ``drmsupported``; any true
  event makes the device true); the output keeps the name ``drmenabled``. Skipped, and said so, when the enriched
  CSV has no ``drmsupported`` column (rebuild it with SU-4);
* ``..._6001_fail_then_success_devices.csv`` -- devices with a 6001 followed by a successful session
  (``is_success``, i.e. ``DESTROY``), read from the local per-date ``<date>_session.csv`` playback outcomes
  (SU-10; ``event_start`` is the session time); skipped, and said so, when no such file exists;
* ``..._6001_mixed_webview_devices.csv`` -- devices whose 6001 events appear both in and outside a webview.

Rows with an ``unknown`` period are not in the before/after tables (counted in the summary). ``GUEST.*``
households are per-install, so device tables flag them (``guest_household``). Local files only; rerunning
overwrites the outputs.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, load_daily  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.playback import is_success  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_versions_devices")
PERIODS = ("before", "after")
UNKNOWN = "unknown"
BASE_EVENTS = "6001 events"
INPUT_ARTIFACT = "shaka6001_enriched"
SESSION_ARTIFACT = "session"
VERSION_FIELDS = [
    "tenant", "base", "group", "before_events", "before_share", "before_devices",
    "after_events", "after_share", "after_devices", "share_change",
]
DRM_DEVICE_FIELDS = ["tenant", "device_id", "device_model", "events", "drmenabled", "guest_household"]
DRM_SUMMARY_FIELDS = ["tenant", "base", "drmenabled", "devices", "device_share", "events", "event_share"]
FAIL_SUCCESS_FIELDS = [
    "tenant", "device_id", "device_model", "first_6001_utc", "first_success_after_utc",
    "successes_after_first_6001", "guest_household",
]
MIXED_FIELDS = ["tenant", "device_id", "device_model", "webview_events", "non_webview_events", "guest_household"]
REQUIRED_COLUMNS = ("device_id", "period", "chrome_version", "os_name", "os_version", "is_webview")


class VersionsDevicesError(Exception):
    """Raised for missing or malformed inputs."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise VersionsDevicesError(f"input file not found: {path}")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise VersionsDevicesError(f"cannot read {path}: {exc}") from exc


def _require_columns(rows: list[dict[str, str]], columns: Iterable[str], source: str) -> None:
    if rows:
        missing = [c for c in columns if c not in rows[0]]
        if missing:
            raise VersionsDevicesError(f"{source} is missing column(s) {missing}")


def load_enriched(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(path)
    _require_columns(rows, REQUIRED_COLUMNS, str(path))
    return rows


def chrome_major(chrome_version: str | None) -> str:
    """Major part of ``156.0.8078.47`` -> ``156``; ``unknown`` when absent or not numeric."""
    major = (chrome_version or "").strip().split(".", 1)[0]
    return major if major.isdigit() else UNKNOWN


def android_version(row: dict[str, str]) -> str:
    """Android version as parsed; non-Android rows share one ``non-android`` bucket."""
    if (row.get("os_name") or "") != "Android":
        return "non-android"
    return (row.get("os_version") or "").strip() or UNKNOWN


def is_true(value: object) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def normalize_drm(value: str | None) -> str:
    text = (value or "").strip().lower()
    if text in ("true", "1", "yes"):
        return "true"
    if text in ("false", "0", "no"):
        return "false"
    return UNKNOWN


def _share(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def version_table(rows: list[dict[str, str]], group_of, tenant: str) -> list[dict]:
    """Per group: events and distinct devices per period plus each period's event share and the change."""
    events: dict[tuple[str, str], int] = defaultdict(int)
    devices: dict[tuple[str, str], set[str]] = defaultdict(set)
    totals = dict.fromkeys(PERIODS, 0)
    for row in rows:
        period = row.get("period", "")
        if period not in PERIODS:
            continue
        group = group_of(row)
        events[(group, period)] += 1
        totals[period] += 1
        if row.get("device_id"):
            devices[(group, period)].add(row["device_id"])
    out = []
    for group in sorted({g for g, _ in events}, key=_group_sort_key):
        b, a = events[(group, "before")], events[(group, "after")]
        before_share, after_share = _share(b, totals["before"]), _share(a, totals["after"])
        out.append({
            "tenant": tenant, "base": BASE_EVENTS, "group": group,
            "before_events": b, "before_share": before_share, "before_devices": len(devices[(group, "before")]),
            "after_events": a, "after_share": after_share, "after_devices": len(devices[(group, "after")]),
            "share_change": round(after_share - before_share, 6),
        })
    return out


def _group_sort_key(group: str) -> tuple[int, list]:
    parts = [int(p) if p.isdigit() else -1 for p in group.split(".")]
    return (1, []) if not group[:1].isdigit() else (0, parts)


def group_devices(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_device: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("device_id"):
            by_device[row["device_id"]].append(row)
    return by_device


def _device_model(device_rows: list[dict[str, str]]) -> str:
    return next((r["device_model"] for r in device_rows if r.get("device_model")), "")


def _is_guest(device_rows: list[dict[str, str]]) -> bool:
    return any((r.get("household_id") or "").startswith("GUEST.") for r in device_rows)


def mixed_webview_devices(rows: list[dict[str, str]], tenant: str) -> list[dict]:
    """Devices with 6001 events both inside and outside a webview."""
    out = []
    for device_id, device_rows in sorted(group_devices(rows).items()):
        wv = sum(is_true(r.get("is_webview")) for r in device_rows)
        if 0 < wv < len(device_rows):
            out.append({
                "tenant": tenant, "device_id": device_id, "device_model": _device_model(device_rows),
                "webview_events": wv, "non_webview_events": len(device_rows) - wv,
                "guest_household": _is_guest(device_rows),
            })
    return out


def drm_by_device(rows: list[dict[str, str]]) -> dict[str, str]:
    """Per device: the enriched ``drmsupported`` column (any true wins), else unknown."""
    result: dict[str, str] = {}
    for device_id, device_rows in group_devices(rows).items():
        values = {normalize_drm(r.get("drmsupported")) for r in device_rows} - {UNKNOWN}
        result[device_id] = "true" if "true" in values else next(iter(values), UNKNOWN)
    return result


def drm_tables(rows: list[dict[str, str]], tenant: str) -> tuple[list[dict], list[dict]]:
    by_device = group_devices(rows)
    drm = drm_by_device(rows)
    device_rows_out = [
        {"tenant": tenant, "device_id": d, "device_model": _device_model(r), "events": len(r),
         "drmenabled": drm[d], "guest_household": _is_guest(r)}
        for d, r in sorted(by_device.items())
    ]
    total_devices, total_events = len(by_device), sum(len(r) for r in by_device.values())
    summary = []
    for value in ("true", "false", UNKNOWN):
        devs = [d for d in by_device if drm[d] == value]
        ev = sum(len(by_device[d]) for d in devs)
        summary.append({
            "tenant": tenant, "base": "devices with 6001 (events for event_share)", "drmenabled": value,
            "devices": len(devs), "device_share": _share(len(devs), total_devices),
            "events": ev, "event_share": _share(ev, total_events),
        })
    return device_rows_out, summary


def _parse_ts(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _first_present(row: dict[str, str], names: tuple[str, ...]) -> str:
    return next((row[n] for n in names if row.get(n)), "")


def outcomes_from_sessions(session_rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """SU-10 session rows (``deviceId``, ``sessionId``, ``playback_outcome``, ``event_start`` UTC) as outcome rows."""
    out = []
    for row in session_rows:
        if "deviceId" not in row or "playback_outcome" not in row:
            raise VersionsDevicesError("session rows need deviceId and playback_outcome columns")
        out.append({
            "device_id": row.get("deviceId", ""), "session_id": row.get("sessionId", ""),
            "playback_outcome": row.get("playback_outcome", ""), "datetime": row.get("event_start", ""),
        })
    return out


def fail_then_success_devices(rows: list[dict[str, str]], outcomes: list[dict[str, str]], tenant: str) -> list[dict]:
    """Devices whose first 6001 is followed by at least one later session with a success outcome."""
    successes: dict[str, list[datetime]] = defaultdict(list)
    for outcome in outcomes:
        ts = _parse_ts(outcome["datetime"])
        if outcome["device_id"] and ts and is_success(outcome["playback_outcome"]):
            successes[outcome["device_id"]].append(ts)
    out = []
    for device_id, device_rows in sorted(group_devices(rows).items()):
        times = [t for t in (_parse_ts(r.get("datetime")) for r in device_rows) if t]
        if not times:
            continue
        first_fail = min(times)
        later = sorted(t for t in successes.get(device_id, []) if t > first_fail)
        if later:
            out.append({
                "tenant": tenant, "device_id": device_id, "device_model": _device_model(device_rows),
                "first_6001_utc": first_fail.isoformat(), "first_success_after_utc": later[0].isoformat(),
                "successes_after_first_6001": len(later), "guest_household": _is_guest(device_rows),
            })
    return out


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
    os.replace(tmp, path)


def build_parser(default_tenant: str, default_start: date) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=default_start)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=default_tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--input", type=Path, default=None, help="enriched CSV (default: SU-4 output for the range)")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-analyze-versions-devices")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.tenant, config.default_start_date).parse_args(argv)
    if args.end_date < args.start_date:
        print(f"ERROR: end date {args.end_date} is before start date {args.start_date}", file=sys.stderr)
        return 2
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    name = lambda artifact: out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact)  # noqa: E731
    try:
        rows = load_enriched(args.input or name(INPUT_ARTIFACT))
        loaded = load_daily(default_sources(resolver, REPO_ROOT, args.tenant), SESSION_ARTIFACT,
                            date_range(args.start_date, args.end_date))
        outcomes = outcomes_from_sessions(loaded.rows) if loaded.found else None
    except (VersionsDevicesError, LocalDataError) as exc:
        LOGGER.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    tenant = args.tenant
    unknown_period = sum(r.get("period") not in PERIODS for r in rows)
    print(f"tenant={tenant} base={BASE_EVENTS} rows={len(rows)} unknown_period_excluded_from_before_after={unknown_period}")
    write_table(name("6001_by_chrome"), version_table(rows, lambda r: chrome_major(r.get("chrome_version")), tenant), VERSION_FIELDS)
    write_table(name("6001_by_android"), version_table(rows, android_version, tenant), VERSION_FIELDS)
    mixed = mixed_webview_devices(rows, tenant)
    write_table(name("6001_mixed_webview_devices"), mixed, MIXED_FIELDS)
    devices = len(group_devices(rows))
    print(f"devices_with_6001={devices} mixed_webview_devices={len(mixed)} ({_share(len(mixed), devices):.1%} of devices)")
    if rows and "drmsupported" in rows[0]:
        device_rows, summary = drm_tables(rows, tenant)
        write_table(name("6001_drm_devices"), device_rows, DRM_DEVICE_FIELDS)
        write_table(name("6001_drm_summary"), summary, DRM_SUMMARY_FIELDS)
        print("drmenabled " + " ".join(f"{s['drmenabled']}={s['devices']} ({s['device_share']:.1%})" for s in summary))
    else:
        print("drm tables skipped: no drmsupported column in the enriched CSV (rebuild it with build_enriched_events.py)")
    if outcomes is not None:
        recovered = fail_then_success_devices(rows, outcomes, tenant)
        write_table(name("6001_fail_then_success_devices"), recovered, FAIL_SUCCESS_FIELDS)
        print(f"fail_then_success_devices={len(recovered)} ({_share(len(recovered), devices):.1%} of devices with 6001) "
              f"session_dates_missing=" + (",".join(d.isoformat() for d in loaded.missing) or "none"))
    else:
        print("fail-then-success table skipped: no local <date>_session.csv files for the range (run build_6001_cohort.py)")
    LOGGER.info("Wrote version/device cuts to %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
