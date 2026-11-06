"""PNG charts for the session error impact table (``analyze_session_error_impact.py`` output).

Reads ``<start>_<end>_session_error_impact.csv`` from the tenant output folder and writes three PNGs to
``output/<tenant>/charts/``. Base on every chart: tenant, UTC days, unique sessions per day's session file.

* ``<start>_<end>_session_error_impact_counts.png`` -- trend, 6001 sessions vs all sessions, each indexed to the first
  day = 100.
* ``<start>_<end>_session_error_impact_pct_stacked.png`` -- columns, 6001-impacted share of each day's unique sessions.
* ``<start>_<end>_session_error_impact_6001_share.png`` -- trend, 6001's share of each day's error-impacted sessions.

Charts are additive: a missing input or a ``ChartError`` is logged and skipped, never raised. Local files only;
rerunning overwrites the PNGs. The ``all`` row of the table is not charted.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Iterable
from datetime import date, datetime
from functools import partial
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.analyze_session_error_impact import ALL_DAY, OUTPUT_ARTIFACT  # noqa: E402
from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from scripts.lib.local_data import SLUG  # noqa: E402
from src.lib.charts.columns import Column, render_columns  # noqa: E402
from src.lib.charts.errors import ChartError  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402
from src.lib.charts.trend import TrendReference, TrendSeries, render_trend  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.chart_session_error_impact")
REQUIRED_COLUMNS = (
    "day", "unique_sessions", "error_sessions", "sessions_6001", "other_error_sessions",
    "error_sessions_in_session_file", "sessions_6001_in_session_file",
)


class ChartInputError(Exception):
    """The table CSV is missing, unreadable or lacks columns."""


def _int(row: dict[str, str], column: str) -> int:
    try:
        return int(row[column])
    except (KeyError, ValueError) as exc:
        raise ChartInputError(f"bad {column!r} in row {row.get('day')!r}") from exc


def day_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """The per-day rows (the ``all`` total dropped), in date order."""
    return sorted((r for r in rows if r.get("day") != ALL_DAY), key=lambda r: r["day"])


def _day_labels(days: list[dict[str, str]]) -> list[str]:
    return [datetime.fromisoformat(r["day"]).strftime("%-d %b") for r in days]


def session_share_values(rows: list[dict[str, str]]) -> tuple[list[str], list[float], list[int]]:
    """Day labels, 6001-impacted share (%) of each day's unique sessions, and each day's 6001 session count."""
    days = day_rows(rows)
    code = [_int(r, "sessions_6001_in_session_file") for r in days]
    unique = [_int(r, "unique_sessions") for r in days]
    if any(u <= 0 or c < 0 or c > u for c, u in zip(code, unique, strict=True)):
        raise ChartInputError("6001 sessions exceed unique sessions; inconsistent table")
    return _day_labels(days), [100 * c / u for c, u in zip(code, unique, strict=True)], code


def error_share_values(rows: list[dict[str, str]]) -> tuple[list[str], list[float]]:
    """Day labels and 6001's share (%) of each day's error-impacted sessions."""
    days = day_rows(rows)
    errors = [_int(r, "error_sessions") for r in days]
    code = [_int(r, "sessions_6001") for r in days]
    if any(e <= 0 or c > e for c, e in zip(code, errors, strict=True)):
        raise ChartInputError("6001 sessions exceed error sessions; inconsistent table")
    return _day_labels(days), [100 * c / e for c, e in zip(code, errors, strict=True)]


def indexed_values(rows: list[dict[str, str]]) -> tuple[list[str], list[float], list[float]]:
    """Day labels and, indexed to the first day = 100, the 6001 session counts and all unique sessions."""
    days = day_rows(rows)
    code = [_int(r, "sessions_6001") for r in days]
    unique = [_int(r, "unique_sessions") for r in days]
    if not days or code[0] <= 0 or unique[0] <= 0:
        raise ChartInputError("the first day needs sessions to index against")
    return _day_labels(days), [100 * c / code[0] for c in code], [100 * u / unique[0] for u in unique]


def _span(values: list[float], pad: float, step: float) -> tuple[float, float, list[float]]:
    lo = step * ((min(values) - pad) // step)
    hi = step * (-(-(max(values) + pad) // step))
    return lo, hi, [lo + step * i for i in range(int((hi - lo) / step) + 1)]


def _share_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, shares, _ = session_share_values(rows)
    return render_columns(
        [Column(label, v, f"{v:.1f}%", "red" if i == len(shares) - 1 else "dim_red") for i, (label, v) in enumerate(zip(labels, shares))],
        title=f"6001 now touches {shares[-1]:.0f}% of sessions, up from {shares[0]:.0f}%",
        subtitle="Share of each day's unique sessions that hit a 6001 error", footer=scope)


def _error_share_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, shares = error_share_values(rows)
    lo, hi, ticks = _span(shares, 5.0, 5.0)
    fmt = lambda v: f"{v:.0f}%"  # noqa: E731
    return render_trend(
        labels, [TrendSeries("6001", shares, "red", end_text=f"{shares[-1]:.1f}%", label_points=range(len(shares) - 1))],
        title=f"6001 is {shares[-1]:.0f}% of all error-impacted sessions",
        subtitle="Share of each day's error-impacted sessions that carry a 6001 error",
        footer=scope, lo=lo, hi=hi, ticks=ticks, value_fmt=lambda v: f"{v:.1f}%", tick_fmt=fmt)


def _indexed_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, code, total = indexed_values(rows)
    lo, hi, ticks = _span(code + total, 10.0, 25.0)
    fmt = lambda v: f"{v:.0f}"  # noqa: E731
    return render_trend(
        labels,
        [TrendSeries("6001 sessions", code, "red", end_text=f"6001 sessions  {fmt(code[-1])}"),
         TrendSeries("all sessions", total, "slate", end_text=f"all sessions  {fmt(total[-1])}")],
        title=f"6001 sessions grew {code[-1] - 100:.0f}% while all sessions moved {total[-1] - 100:+.0f}%",
        subtitle=f"Unique sessions per day, indexed to {labels[0]} = 100",
        footer=scope, lo=lo, hi=hi, ticks=ticks, value_fmt=fmt, reference=TrendReference(100.0, f"{labels[0]} level"))


def build_charts(rows: list[dict[str, str]], *, tenant: str, start: date, end: date) -> dict[str, Callable[[], bytes]]:
    """Artifact suffix -> render callable; nothing is drawn until called, so one bad chart cannot block the others."""
    scope = f"tenant {tenant}, {start.isoformat()} to {end.isoformat()}"
    return {
        f"{OUTPUT_ARTIFACT}_counts": partial(_indexed_chart, rows, scope),
        f"{OUTPUT_ARTIFACT}_pct_stacked": partial(_share_chart, rows, scope),
        f"{OUTPUT_ARTIFACT}_6001_share": partial(_error_share_chart, rows, scope),
    }


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


def read_table(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ChartInputError(f"input not found: {path}")
    try:
        rows = list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError) as exc:
        raise ChartInputError(f"cannot read {path}: {exc}") from exc
    if rows and (missing := [c for c in REQUIRED_COLUMNS if c not in rows[0]]):
        raise ChartInputError(f"{path} is missing columns: {', '.join(missing)}")
    return rows


def build_parser(default_tenant: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 11, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 11, 5))
    parser.add_argument("--tenant", default=default_tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-chart-session-error-impact")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config.tenant).parse_args(argv)
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    table = out_dir / resolver.format_range_filename(args.start_date, args.end_date, OUTPUT_ARTIFACT)
    try:
        rows = read_table(table)
    except ChartInputError as exc:
        LOGGER.warning("chart input skipped: %s", exc)
        return 0
    charts = build_charts(rows, tenant=args.tenant, start=args.start_date, end=args.end_date)
    written = write_charts(charts, out_dir.parent, args.tenant,
                           lambda a: resolver.format_range_filename(args.start_date, args.end_date, a, extension="png"))
    for item in written:
        print(f"wrote {item}")
    LOGGER.info("Wrote %d of %d charts (tenant %s, UTC days)", len(written), len(charts), args.tenant)
    return 0


if __name__ == "__main__":
    sys.exit(main())
