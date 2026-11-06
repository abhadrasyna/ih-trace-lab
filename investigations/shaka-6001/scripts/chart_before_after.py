"""PNG charts for the Shaka 6001 before/after tables (SU-5 and SU-6 outputs).

Reads, from the tenant output folder, the CSVs written by ``analyze_before_after.py`` and
``analyze_versions_devices.py`` plus the SU-4 enriched CSV, and writes PNGs to ``output/<tenant>/charts/``:

* ``<start>_<end>_6001_webview_share.png`` -- 100% stacked bar, webview vs non-webview share of events before/after.
* ``<start>_<end>_6001_top_models.png`` -- horizontal bar, top device models by 6001 events (6001 dominates, so no donut).
* ``<start>_<end>_6001_webview_daily_trend.png`` -- signed line, each IST day's webview share of events minus the
  before-period webview share (percentage points).
* ``<start>_<end>_6001_chrome_versions.png`` -- stacked bar of events per Chrome major, before vs after.

Base: events (``GUEST.*`` ids only matter for device counts, which are not charted). Charts are additive: a missing
input or a ``ChartError`` is logged and skipped, never raised, so the CSVs are never blocked. Local files only;
rerunning overwrites the PNGs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.local_data import SLUG  # noqa: E402
from src.lib.charts.errors import ChartError  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402
from src.lib.charts.signed_line import render_signed_line  # noqa: E402
from src.lib.charts.stacked_bar import render_stacked_bar  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.chart_before_after")
WEBVIEW_ARTIFACT = "6001_before_after_webview"
MODEL_ARTIFACT = "6001_before_after_model"
CHROME_ARTIFACT = "6001_by_chrome"
ENRICHED_ARTIFACT = "shaka6001_enriched"
PERIODS = ("before", "after")
WEBVIEW_GROUPS = ("webview", "non_webview", "unknown")
TOP_MODELS = 10
MAX_CHROME_VERSIONS = 12
BASE = "6001 events"


class ChartInputError(Exception):
    """A chart input CSV is missing or unreadable."""


def _int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError as exc:
        raise ChartInputError(f"not a number: {value!r}") from exc


def webview_share_values(rows: Iterable[dict[str, str]]) -> tuple[list[str], dict[str, list[float]], list[int]]:
    """Stack labels (before, after), one event-count series per webview group, and each stack's event total."""
    by_group = {r["webview_group"]: r for r in rows}
    series = {g: [float(_int(by_group.get(g, {}).get(f"events_{p}"))) for p in PERIODS] for g in WEBVIEW_GROUPS}
    series = {g: v for g, v in series.items() if g != "unknown" or any(v)}
    totals = [int(sum(v[i] for v in series.values())) for i in range(len(PERIODS))]
    return [f"{p} ({totals[i]:,} events)" for i, p in enumerate(PERIODS)], series, totals


def top_model_values(rows: Iterable[dict[str, str]], top: int = TOP_MODELS) -> tuple[list[str], list[float], int]:
    """Top ``top`` models by before+after events (descending, ties by name) and the all-model event total."""
    counts = {r["device_model"]: _int(r["events_before"]) + _int(r["events_after"])
              for r in rows if r.get("level") == "model"}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return [m for m, _ in ranked], [float(c) for _, c in ranked], sum(counts.values())


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def daily_webview_delta(rows: Iterable[dict[str, str]], tz: ZoneInfo) -> tuple[list[str], list[float], float]:
    """IST days, each day's webview share (%) minus the before-period share, and that baseline share (%)."""
    day_wv: dict[str, int] = defaultdict(int)
    day_all: dict[str, int] = defaultdict(int)
    before_wv = before_all = 0
    for row in rows:
        if (row.get("period") or "") not in PERIODS:
            continue
        ts = _parse_utc(row.get("datetime", ""))
        if ts is None:
            continue
        is_wv = (row.get("is_webview") or "").strip().lower() == "true"
        day = ts.astimezone(tz).date().isoformat()
        day_all[day] += 1
        day_wv[day] += is_wv
        if row["period"] == "before":
            before_all += 1
            before_wv += is_wv
    baseline = 100 * before_wv / before_all if before_all else 0.0
    days = sorted(day_all)
    return days, [100 * day_wv[d] / day_all[d] - baseline for d in days], baseline


def chrome_version_values(rows: Iterable[dict[str, str]],
                          limit: int = MAX_CHROME_VERSIONS) -> tuple[list[str], dict[str, list[float]], int]:
    """Top Chrome majors by events as stack labels, before/after series, and the all-version event total."""
    counts = {r["group"]: (_int(r["before_events"]), _int(r["after_events"])) for r in rows}
    ranked = sorted(counts.items(), key=lambda kv: (-sum(kv[1]), kv[0]))[:limit]
    ranked.sort(key=lambda kv: (not kv[0].isdigit(), int(kv[0]) if kv[0].isdigit() else 0, kv[0]))
    series = {p: [float(c[i]) for _, c in ranked] for i, p in enumerate(PERIODS)}
    return [v for v, _ in ranked], series, sum(sum(c) for c in counts.values())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ChartInputError(f"input not found: {path}")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError) as exc:
        raise ChartInputError(f"cannot read {path}: {exc}") from exc


def _require(rows: list[dict[str, str]], columns: tuple[str, ...], source: Path) -> None:
    if rows and (missing := [c for c in columns if c not in rows[0]]):
        raise ChartInputError(f"{source} is missing columns: {', '.join(missing)}")


def _title_range(tenant: str, start: date, end: date) -> str:
    return f"{tenant}, {start.isoformat()} to {end.isoformat()}"


def _webview_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, series, _ = webview_share_values(rows)
    return render_stacked_bar(
        labels, series, normalize=True, legend="above",
        title="6001 events: webview vs non-webview share, before vs after",
        subtitle=f"Base: 6001 events, {scope}; labels show events and share of each period",
        colours={"non_webview": "amber"})


def _models_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    names, values, total = top_model_values(rows)
    return render_stacked_bar(
        names, {"events": values}, horizontal=True, total=float(total), legend=False,
        title=f"Top {len(names)} device models by 6001 events",
        subtitle=f"Base: 6001 events (before + after), {scope}; share of all {total:,} events")


def _trend_chart(rows: list[dict[str, str]], scope: str, tz: ZoneInfo) -> bytes:
    days, deltas, baseline = daily_webview_delta(rows, tz)
    span = f"day 0 = {days[0]}, last = {days[-1]}" if days else "no days"
    return render_signed_line(
        list(range(len(days))), deltas,
        title="Daily webview share of 6001 events vs before-period share (pp)",
        subtitle=f"Base: 6001 events per IST day, {scope}; {span}; before-period share {baseline:.1f}%")


def _chrome_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, series, total = chrome_version_values(rows)
    return render_stacked_bar(
        labels, series, legend="above", total=float(total),
        title="6001 events by Chrome major version, before vs after",
        subtitle=f"Base: 6001 events, {scope}; top {len(labels)} versions, share of all {total:,} events")


def build_charts(
    web_rows: list[dict[str, str]] | None,
    model_rows: list[dict[str, str]] | None,
    enriched_rows: list[dict[str, str]] | None,
    chrome_rows: list[dict[str, str]] | None,
    *,
    tenant: str,
    start: date,
    end: date,
    tz: ZoneInfo,
) -> dict[str, Callable[[], bytes]]:
    """Artifact name -> render callable for each chart whose input was supplied.

    Nothing is computed or drawn here: each callable extracts its own values from its own rows when called, so a
    bad cell fails only that chart (see ``write_charts``) and no chart can see another chart's data.
    """
    scope = _title_range(tenant, start, end)
    charts: dict[str, Callable[[], bytes]] = {}
    if web_rows is not None:
        charts["6001_webview_share"] = partial(_webview_chart, web_rows, scope)
    if model_rows is not None:
        charts["6001_top_models"] = partial(_models_chart, model_rows, scope)
    if enriched_rows is not None:
        charts["6001_webview_daily_trend"] = partial(_trend_chart, enriched_rows, scope, tz)
    if chrome_rows is not None:
        charts["6001_chrome_versions"] = partial(_chrome_chart, chrome_rows, scope)
    return charts


def write_charts(charts: dict[str, Callable[[], bytes]], output_dir: Path, tenant: str,
                 filename: Callable[[str], str]) -> list[Path]:
    """Render and save each chart; a chart or bad-cell error is logged and skipped, never raised."""
    written: list[Path] = []
    for suffix, render in charts.items():
        try:
            written.append(write_chart_png(render(), output_dir, tenant, filename(suffix)))
        except (ChartError, ChartInputError, KeyError, ValueError, OverflowError, OSError) as exc:
            LOGGER.error("chart %s skipped: %s", suffix, exc)
    return written


def _optional(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]] | None:
    try:
        rows = read_csv(path)
        _require(rows, columns, path)
        return rows
    except ChartInputError as exc:
        LOGGER.warning("chart input skipped: %s", exc)
        return None


def build_parser(default_start: date, default_tenant: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=default_start)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=default_tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-chart-before-after")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.default_start_date, config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)

    def path(artifact: str) -> Path:
        return out_dir / resolver.format_range_filename(args.start_date, args.end_date, artifact)

    web = _optional(path(WEBVIEW_ARTIFACT), ("webview_group", "events_before", "events_after"))
    models = _optional(path(MODEL_ARTIFACT), ("level", "device_model", "events_before", "events_after"))
    enriched = _optional(path(ENRICHED_ARTIFACT), ("datetime", "period", "is_webview"))
    chrome = _optional(path(CHROME_ARTIFACT), ("group", "before_events", "after_events"))
    charts = build_charts(web, models, enriched, chrome, tenant=args.tenant, start=args.start_date,
                          end=args.end_date, tz=config.timezone)
    written = write_charts(charts, out_dir.parent, args.tenant,
                           lambda a: resolver.format_range_filename(args.start_date, args.end_date, a, extension="png"))
    for item in written:
        print(f"wrote {item}")
    LOGGER.info("Wrote %d of %d charts (base: %s, tenant %s)", len(written), len(charts), BASE, args.tenant)
    return 0


if __name__ == "__main__":
    sys.exit(main())
