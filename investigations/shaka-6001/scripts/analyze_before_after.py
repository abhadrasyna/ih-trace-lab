"""Before/after Shaka 6001 counts by webview and by device model (and model + build).

Reads the SU-4 enriched CSV (``<start>_<end>_shaka6001_enriched.csv``, one row per deduplicated 6001 debug event,
UTC timestamps already classified into ``before``/``after``/``unknown`` by app version first). For each group it
reports events, distinct devices and distinct sessions per period, each period's share of that period's events and
the change in share (after minus before, percentage points). Rows with an ``unknown`` period are counted in the
summary only. ``GUEST.*`` device ids are per-install, so they are counted in separate ``guest_devices_*`` columns
and never in ``devices_*``. Base: events (sessions/devices where named); tenant: ``--tenant``. Local files only;
rerunning overwrites the outputs.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.local_data import SLUG  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.analyze_before_after")
INPUT_ARTIFACT = "shaka6001_enriched"
WEBVIEW_ARTIFACT = "6001_before_after_webview"
MODEL_ARTIFACT = "6001_before_after_model"
PERIODS = ("before", "after")
GUEST_PREFIX = "GUEST."
WEBVIEW_LABELS = {"true": "webview", "false": "non_webview"}
UNKNOWN_LABEL = "unknown"
LEVEL_MODEL = "model"
LEVEL_MODEL_BUILD = "model_build"
REQUIRED_COLUMNS = ("period", "device_id", "session_id", "is_webview", "device_model", "build_id")
SHARE_BASE = "events"


class BeforeAfterError(Exception):
    """The enriched input is missing or does not have the expected columns."""


def _metric_columns() -> list[str]:
    cols: list[str] = []
    for period in PERIODS:
        cols += [f"events_{period}", f"devices_{period}", f"guest_devices_{period}", f"sessions_{period}",
                 f"share_{period}_pct"]
    return cols + ["events_change", "share_change_pp"]


WEBVIEW_FIELDS = ["tenant", "base", "webview_group", *_metric_columns()]
MODEL_FIELDS = ["tenant", "base", "level", "device_model", "build_id", *_metric_columns()]


def webview_label(value: str | None) -> str:
    return WEBVIEW_LABELS.get((value or "").strip().lower(), UNKNOWN_LABEL)


def _clean(value: str | None) -> str:
    return (value or "").strip() or UNKNOWN_LABEL


class _Group:
    """Per-period event count plus distinct device and session sets for one group key."""

    def __init__(self) -> None:
        self.events = dict.fromkeys(PERIODS, 0)
        self.devices: dict[str, set[str]] = {p: set() for p in PERIODS}
        self.guests: dict[str, set[str]] = {p: set() for p in PERIODS}
        self.sessions: dict[str, set[str]] = {p: set() for p in PERIODS}

    def add(self, period: str, device_id: str, session_id: str) -> None:
        self.events[period] += 1
        if device_id.startswith(GUEST_PREFIX):
            self.guests[period].add(device_id)
        elif device_id:
            self.devices[period].add(device_id)
        if session_id:
            self.sessions[period].add(session_id)


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 2) if total else 0.0


def _metrics(group: _Group, totals: dict[str, int]) -> dict:
    row: dict = {}
    for period in PERIODS:
        row[f"events_{period}"] = group.events[period]
        row[f"devices_{period}"] = len(group.devices[period])
        row[f"guest_devices_{period}"] = len(group.guests[period])
        row[f"sessions_{period}"] = len(group.sessions[period])
        row[f"share_{period}_pct"] = _pct(group.events[period], totals[period])
    row["events_change"] = group.events["after"] - group.events["before"]
    row["share_change_pp"] = round(row["share_after_pct"] - row["share_before_pct"], 2)
    return row


def _sort_key(row: dict) -> tuple:
    return (-(row["events_before"] + row["events_after"]),)


def _validate(rows: list[dict[str, str]]) -> None:
    if rows:
        missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
        if missing:
            raise BeforeAfterError(f"enriched input lacks columns: {', '.join(missing)}")


def summarize(rows: Iterable[dict[str, str]], tenant: str) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Webview rows, model rows (model and model+build levels) and period row counts. No rows gives zeros."""
    materialized = list(rows)
    _validate(materialized)
    webview: dict[str, _Group] = defaultdict(_Group)
    models: dict[tuple[str, str, str], _Group] = defaultdict(_Group)
    totals = dict.fromkeys(PERIODS, 0)
    counts = {"before": 0, "after": 0, "unknown": 0}
    for row in materialized:
        period = (row.get("period") or "").strip()
        if period not in PERIODS:
            counts["unknown"] += 1
            continue
        counts[period] += 1
        totals[period] += 1
        device, session = (row.get("device_id") or "").strip(), (row.get("session_id") or "").strip()
        model, build = _clean(row.get("device_model")), _clean(row.get("build_id"))
        webview[webview_label(row.get("is_webview"))].add(period, device, session)
        models[(LEVEL_MODEL, model, "")].add(period, device, session)
        models[(LEVEL_MODEL_BUILD, model, build)].add(period, device, session)
    for label in WEBVIEW_LABELS.values():
        webview.setdefault(label, _Group())
    web_rows = [{"tenant": tenant, "base": SHARE_BASE, "webview_group": k, **_metrics(g, totals)}
                for k, g in webview.items()]
    model_rows = [{"tenant": tenant, "base": SHARE_BASE, "level": lv, "device_model": m, "build_id": b,
                   **_metrics(g, totals)} for (lv, m, b), g in models.items()]
    web_rows.sort(key=_sort_key)
    model_rows.sort(key=lambda r: (r["level"], *_sort_key(r), r["device_model"], r["build_id"]))
    return web_rows, model_rows, counts


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write through a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        CsvFileWriter().write_rows(str(tmp), rows, fieldnames)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_enriched(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise BeforeAfterError(f"enriched events file not found: {path} (run build_enriched_events.py first)")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError) as exc:
        raise BeforeAfterError(f"cannot read {path}: {exc}") from exc


def build_parser(default_start: date, default_tenant: str) -> argparse.ArgumentParser:
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

    init_logging("shaka-6001-analyze-before-after")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.default_start_date, config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    in_path = args.input or out_dir / resolver.format_range_filename(args.start_date, args.end_date, INPUT_ARTIFACT)
    try:
        web_rows, model_rows, counts = summarize(read_enriched(in_path), args.tenant)
    except BeforeAfterError as exc:
        LOGGER.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    web_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, WEBVIEW_ARTIFACT)
    model_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, MODEL_ARTIFACT)
    write_rows(web_path, web_rows, WEBVIEW_FIELDS)
    write_rows(model_path, model_rows, MODEL_FIELDS)
    print(f"tenant={args.tenant} base=events before={counts['before']} after={counts['after']} "
          f"unknown_period_excluded={counts['unknown']}")
    print(f"wrote {web_path}\nwrote {model_path}")
    LOGGER.info("Wrote %d webview and %d model rows", len(web_rows), len(model_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
