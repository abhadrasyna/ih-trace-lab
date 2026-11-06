"""PNG charts for the session error impact table (``analyze_session_error_impact.py`` output).

Reads ``<start>_<end>_session_error_impact.csv`` from the tenant output folder and writes three PNGs to
``output/<tenant>/charts/``. Base on every chart: tenant, UTC days, unique sessions per day's session file.

* ``<start>_<end>_session_error_impact_counts.png`` -- per UTC day, unique sessions next to 6001-impacted sessions (the
  shared lib has no grouped bar, so it is a one-series bar per day and measure; 6001 is tiny next to the sessions, so
  every bar is labelled with its count).
* ``<start>_<end>_session_error_impact_pct_stacked.png`` -- 100% stack per day of unique sessions: 6001-impacted,
  other-error and no-error. Uses the sessions found in the session file, so it adds up to 100%.
* ``<start>_<end>_session_error_impact_6001_share.png`` -- per day, 6001 vs other-error split of all error-impacted
  sessions (counts and share in the labels).

Charts are additive: a missing input or a ``ChartError`` is logged and skipped, never raised. Local files only;
rerunning overwrites the PNGs. The ``all`` row of the table is not charted.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Iterable
from datetime import date
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
from src.lib.charts.errors import ChartError  # noqa: E402
from src.lib.charts.output import write_chart_png  # noqa: E402
from src.lib.charts.stacked_bar import render_stacked_bar  # noqa: E402
from src.lib.charts.theme import DARK  # noqa: E402
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


def counts_values(rows: list[dict[str, str]]) -> tuple[list[str], list[float], list[str]]:
    """Bar labels (one per day and measure), their counts and per-bar colours."""
    labels: list[str] = []
    values: list[float] = []
    colours: list[str] = []
    for row in day_rows(rows):
        labels += [f"{row['day'][5:]} all", f"{row['day'][5:]} 6001"]
        values += [float(_int(row, "unique_sessions")), float(_int(row, "sessions_6001"))]
        colours += [DARK.ink, DARK.red]
    return labels, values, colours


def pct_stacked_values(rows: list[dict[str, str]]) -> tuple[list[str], dict[str, list[float]]]:
    """Per-day stacks that sum to the day's unique sessions: 6001, other-error, no-error (all in the session file)."""
    days = day_rows(rows)
    code = [_int(r, "sessions_6001_in_session_file") for r in days]
    error = [_int(r, "error_sessions_in_session_file") for r in days]
    unique = [_int(r, "unique_sessions") for r in days]
    series = {
        "6001-impacted": [float(c) for c in code],
        "other error": [float(e - c) for e, c in zip(error, code, strict=True)],
        "no error": [float(u - e) for u, e in zip(unique, error, strict=True)],
    }
    if any(v < 0 for values in series.values() for v in values):
        raise ChartInputError("matched error sessions exceed unique sessions; inconsistent table")
    return [f"{r['day'][5:]}\n{u:,} sessions" for r, u in zip(days, unique, strict=True)], series


def share_values(rows: list[dict[str, str]]) -> tuple[list[str], dict[str, list[float]]]:
    """Per-day stacks of all error-impacted sessions: 6001 vs other-error."""
    days = day_rows(rows)
    labels = [f"{r['day'][5:]}\n{_int(r, 'error_sessions'):,} errors" for r in days]
    return labels, {
        "6001-impacted": [float(_int(r, "sessions_6001")) for r in days],
        "other error": [float(_int(r, "other_error_sessions")) for r in days],
    }


def _counts_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, values, colours = counts_values(rows)
    return render_stacked_bar(
        labels, {"sessions": values}, bar_colours=colours, horizontal=True, legend=False,
        title="Unique sessions vs 6001-impacted sessions per day",
        subtitle=f"Base: unique sessions per UTC day, {scope}")


def _pct_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, series = pct_stacked_values(rows)
    return render_stacked_bar(
        labels, series, normalize=True, legend="above", colours={"6001-impacted": "red", "other error": "amber", "no error": "green"},
        title="Share of unique sessions by error impact per day",
        subtitle=f"Base: unique sessions per UTC day, {scope}")


def _share_chart(rows: list[dict[str, str]], scope: str) -> bytes:
    labels, series = share_values(rows)
    return render_stacked_bar(
        labels, series, normalize=True, legend="above", colours={"6001-impacted": "red", "other error": "amber"},
        title="6001 share of error-impacted sessions per day",
        subtitle=f"Base: error sessions per UTC day, {scope}")


def build_charts(rows: list[dict[str, str]], *, tenant: str, start: date, end: date) -> dict[str, Callable[[], bytes]]:
    """Artifact suffix -> render callable; nothing is drawn until called, so one bad chart cannot block the others."""
    scope = f"tenant {tenant}, {start.isoformat()} to {end.isoformat()}"
    return {
        f"{OUTPUT_ARTIFACT}_counts": partial(_counts_chart, rows, scope),
        f"{OUTPUT_ARTIFACT}_pct_stacked": partial(_pct_chart, rows, scope),
        f"{OUTPUT_ARTIFACT}_6001_share": partial(_share_chart, rows, scope),
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
