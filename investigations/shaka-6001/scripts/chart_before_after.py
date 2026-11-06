"""PNG charts for the Shaka 6001 before/after tables (SU-5 and SU-6 outputs).

Reads, from the tenant output folder, the CSVs written by ``analyze_before_after.py`` and
``analyze_versions_devices.py`` plus the SU-4 enriched CSV, and writes PNGs to ``output/<tenant>/charts/``:

* ``<start>_<end>_6001_webview_share.png`` -- rate bars, non-webview share of 6001 events before vs after.
* ``<start>_<end>_6001_top_models.png`` -- rate bars, each top device model's share of all 6001 events.
* ``<start>_<end>_6001_webview_daily_trend.png`` -- trend, each IST day's webview share of events minus the
  before-period webview share (percentage points), against a before-upgrade reference line.
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
from src.lib.charts.rate_bars import RateRow, render_rate_bars  # noqa: E402
from src.lib.charts.stacked_bar import render_stacked_bar  # noqa: E402
from src.lib.charts.trend import TrendReference, TrendSeries, render_trend  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.chart_before_after")
WEBVIEW_ARTIFACT = "6001_before_after_webview"
MODEL_ARTIFACT = "6001_before_after_model"
CHROME_ARTIFACT = "6001_by_chrome"
ENRICHED_ARTIFACT = "shaka6001_enriched"
PERIODS = ("before", "after")
WEBVIEW_GROUPS = ("webview", "non_webview", "unknown")
TOP_MODELS = 6
MAX_CHROME_VERSIONS = 12
BASE = "6001 events"


class ChartInputError(Exception):
    """A chart input CSV is missing or unreadable."""


def _int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError as exc:
        raise ChartInputError(f"not a number: {value!r}") from exc


def non_webview_counts(rows: Iterable[dict[str, str]]) -> tuple[list[int], list[int]]:
    """Non-webview events and all events per period (before, after); unknown-group events count in the total."""
    by_group = {r["webview_group"]: r for r in rows}
    per_group = {g: [_int(by_group.get(g, {}).get(f"events_{p}")) for p in PERIODS] for g in WEBVIEW_GROUPS}
    totals = [sum(v[i] for v in per_group.values()) for i in range(len(PERIODS))]
    return per_group["non_webview"], totals


def change_phrase(before: float, after: float) -> str:
    """Plain-words size of a change between two positive rates: ``more than doubled``, ``rose``, ``fell``, ``held``."""
    if before <= 0 or after <= 0 or abs(after - before) < 0.05 * before:
        return "held steady"
    if after >= 2 * before:
        return "more than doubled"
    if after <= before / 2:
        return "more than halved"
    return "rose" if after > before else "fell"


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
    other, totals = non_webview_counts(rows)
    if not all(totals):
        raise ChartInputError("non-webview share needs events in both periods")
    shares = [100 * n / t for n, t in zip(other, totals)]
    verb = change_phrase(shares[0], shares[1])
    return render_rate_bars(
        [RateRow(f"{p.title()} upgrade", shares[i], f"{shares[i]:.1f}%   {other[i]:,} of {totals[i]:,} events",
                 "violet" if i else "dim_violet") for i, p in enumerate(PERIODS)],
        title=f"Non-webview share of 6001 events {verb}",
        subtitle="Share of 6001 events raised outside a webview player, before vs after",
        footer=scope, vmax=max(10.0, 1.4 * max(shares)))


def _models_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    names, values, total = top_model_values(rows)
    if not total:
        raise ChartInputError("no model events")
    shown = 100 * sum(values) / total
    return render_rate_bars(
        [RateRow(n, 100 * v / total, f"{100 * v / total:.1f}%   {int(v):,}", "blue") for n, v in zip(names, values)],
        title=f"Top {len(names)} device models carry {shown:.0f}% of 6001 events",
        subtitle="Each model's share of all 6001 events, before and after combined",
        footer=f"{scope}; {total:,} events in total", vmax=max(10.0, 1.3 * 100 * values[0] / total))


def _trend_chart(rows: list[dict[str, str]], scope: str, tz: ZoneInfo) -> bytes:
    days, deltas, baseline = daily_webview_delta(rows, tz)
    if not days:
        raise ChartInputError("no dated events for the trend")
    lo = min(-1.0, 1.4 * min(deltas))
    hi = max(1.0, 1.4 * max(deltas))
    step = 5.0 if hi - lo > 12 else 2.0
    ticks = [t * step for t in range(int(lo // step), int(hi // step) + 2) if lo <= t * step <= hi]
    labels = [datetime.fromisoformat(d).strftime("%-d %b") for d in days]
    fmt = lambda v: f"{v:+.1f} pp"  # noqa: E731
    return render_trend(
        labels,
        [TrendSeries("webview", deltas, "red", end_text=fmt(deltas[-1]),
                     label_points=range(len(deltas) - 1), labels_below=True)],
        title=f"Webview share moved {fmt(deltas[-1])} against the before-upgrade level",
        subtitle=f"Daily webview share of 6001 events minus the before-period share ({baseline:.1f}%)",
        footer=scope, lo=lo, hi=hi, ticks=ticks, value_fmt=fmt,
        tick_fmt=lambda v: f"{v:+.0f}", reference=TrendReference(0.0, "before-upgrade level"))


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
