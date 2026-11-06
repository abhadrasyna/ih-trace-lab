"""Build the per-event enrichment table for Shaka 6001 from local debug-event exports.

Reads the daily ``*_error_eventdata_codes-6001.csv`` files (table ``ccl_debug_events``, UTC timestamps, one row
per event) for ``--start-date``..``--end-date``, drops exact duplicates by ``messageid`` (first occurrence kept),
flattens ``eventdata`` (including ``drmsupported`` and ``iswebview``, both nested in ``errordescription``;
empty when absent), adds the parsed user-agent fields and the before/after ``period`` (UTC converted to IST
inside the classifier; the version wins over the timestamp, ``period_conflict`` flags a disagreement).
``eventdata_iswebview`` is kept next to the UA-derived ``is_webview`` and the rows where both are known but
disagree are counted. Rows with an unparsed user agent or an ``unknown`` period are kept and only counted. Base: events; tenant: see
``--tenant``. Reads local files only (missing dates are reported, nothing is fetched); rerunning overwrites.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.local_data import SLUG, date_range, default_sources, load_daily  # noqa: E402
from scripts.lib.period import Period, classify_period  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileWriter  # noqa: E402
from src.lib.debug_events import extract_error_app_version, extract_error_client_flags, flatten_row, parse_eventdata  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402
from src.lib.user_agent import parse_user_agent  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.build_enriched_events")
SOURCE_ARTIFACT = "error_eventdata_codes-6001"
OUTPUT_ARTIFACT = "shaka6001_enriched"
UA_SHAPE_UNPARSED = "unparsed"
FIELDNAMES = [
    "datetime", "messageid", "clibversion", "device_id", "household_id", "eventclass", "eventid", "session_id",
    "errorcode", "error_text", "shaka_code", "shaka_message", "position", "app_version", "user_agent",
    "os_name", "os_version", "device_model", "build_id", "chrome_version", "is_webview", "ua_shape",
    "drmsupported", "eventdata_iswebview", "period", "period_conflict",
]
UA_FIELDS = ("os_name", "os_version", "device_model", "build_id", "chrome_version", "is_webview", "ua_shape")


@dataclass(frozen=True)
class EnrichResult:
    rows: list[dict]
    duplicates_removed: int
    missing_messageid: int
    unparsed_ua: int
    bad_timestamp: int
    period_counts: dict[str, int]
    conflicts: int
    webview_disagreements: int
    webview_comparable: int


def _flag_text(value: bool | None) -> str:
    return "" if value is None else str(value).lower()


def parse_utc(value: str | None) -> datetime | None:
    """Parse a table timestamp as UTC; None when absent or malformed."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def dedupe_by_messageid(rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, str]], int, int]:
    """Keep the first row per messageid; rows without one cannot be compared and are all kept."""
    seen: set[str] = set()
    kept: list[dict[str, str]] = []
    removed = missing = 0
    for row in rows:
        message_id = (row.get("messageid") or "").strip()
        if not message_id:
            missing += 1
        elif message_id in seen:
            removed += 1
            continue
        else:
            seen.add(message_id)
        kept.append(row)
    return kept, removed, missing


def enrich_row(row: dict[str, str], config: AnalysisConfig) -> tuple[dict, bool]:
    """One flat enriched row plus whether its timestamp was unusable."""
    flat = flatten_row(row)
    data = parse_eventdata(row.get("eventdata", ""))
    app_version = extract_error_app_version(data) or ""
    flags = extract_error_client_flags(data)
    ua = parse_user_agent(flat.get("user_agent"))
    ts = parse_utc(flat.get("datetime"))
    if ts is None:
        period, conflict = Period.UNKNOWN, False
    else:
        period, conflict = classify_period(ts, app_version or None, config)
    out = {name: flat.get(name) for name in FIELDNAMES if name in flat}
    out.update(messageid=row.get("messageid", ""), clibversion=row.get("clibversion", ""), app_version=app_version)
    out.update({name: ua[name] for name in UA_FIELDS})
    out.update(drmsupported=_flag_text(flags["drmsupported"]), eventdata_iswebview=_flag_text(flags["iswebview"]))
    out.update(period=period.value, period_conflict=conflict)
    return {name: out.get(name, "") for name in FIELDNAMES}, ts is None


def webview_disagrees(row: dict) -> bool:
    """True when the eventdata ``iswebview`` flag and the UA-derived ``is_webview`` are both known and differ."""
    flag = row["eventdata_iswebview"]
    if not flag or row["ua_shape"] == UA_SHAPE_UNPARSED:
        return False
    return (flag == "true") != bool(row["is_webview"])


def enrich_rows(raw_rows: Iterable[dict[str, str]], config: AnalysisConfig) -> EnrichResult:
    """Dedupe then enrich; nothing is dropped except exact messageid duplicates."""
    unique, removed, missing = dedupe_by_messageid(raw_rows)
    enriched: list[dict] = []
    bad_ts = 0
    for row in unique:
        out, ts_bad = enrich_row(row, config)
        bad_ts += ts_bad
        enriched.append(out)
    return EnrichResult(
        rows=enriched,
        duplicates_removed=removed,
        missing_messageid=missing,
        unparsed_ua=sum(r["ua_shape"] == UA_SHAPE_UNPARSED for r in enriched),
        bad_timestamp=bad_ts,
        period_counts=dict(Counter(r["period"] for r in enriched)),
        conflicts=sum(bool(r["period_conflict"]) for r in enriched),
        webview_disagreements=sum(webview_disagrees(r) for r in enriched),
        webview_comparable=sum(bool(r["eventdata_iswebview"]) and r["ua_shape"] != UA_SHAPE_UNPARSED for r in enriched),
    )


def write_enriched(path: Path, rows: list[dict]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, FIELDNAMES)
    os.replace(tmp, path)


def summary_lines(result: EnrichResult, tenant: str, missing: list[date], out_path: Path) -> list[str]:
    counts = result.period_counts
    drm = Counter(r["drmsupported"] for r in result.rows)
    drm.update({"true": 0, "false": 0, "": 0})
    return [
        f"tenant={tenant} base=events rows={len(result.rows)} -> {out_path}",
        f"duplicates_removed_by_messageid={result.duplicates_removed} rows_without_messageid_kept={result.missing_messageid}",
        f"unparsed_user_agents={result.unparsed_ua} (kept)",
        f"period before={counts.get('before', 0)} after={counts.get('after', 0)} unknown={counts.get('unknown', 0)} "
        f"conflict={result.conflicts} bad_timestamp={result.bad_timestamp} (all kept)",
        f"drmsupported true={drm['true']} false={drm['false']} empty={drm['']} (eventdata)",
        f"eventdata_iswebview_vs_ua_is_webview disagree={result.webview_disagreements} "
        f"of {result.webview_comparable} rows with both known",
        "missing_dates=" + (",".join(d.isoformat() for d in missing) or "none"),
    ]


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--artifact", default=SOURCE_ARTIFACT, help="daily source file artifact name")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-build-enriched-events")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    dates = date_range(args.start_date, args.end_date)
    loaded = load_daily(default_sources(resolver, REPO_ROOT, args.tenant), args.artifact, dates)
    if not loaded.found:
        LOGGER.error("No %s files found for %s..%s", args.artifact, args.start_date, args.end_date)
        print(f"ERROR: no local {args.artifact} files for {args.start_date}..{args.end_date}", file=sys.stderr)
        return 2
    result = enrich_rows(loaded.rows, config)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    out_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, OUTPUT_ARTIFACT)
    write_enriched(out_path, result.rows)
    for line in summary_lines(result, args.tenant, loaded.missing, out_path):
        print(line)
    LOGGER.info("Wrote %d enriched events to %s", len(result.rows), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
