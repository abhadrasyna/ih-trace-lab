"""mDRM device and policy report for one OpCo: ``brRef`` vs security level, FairPlay/PlayReady devices, VOD vs linear, failures.

Reads only the saved Lightstep exports (no Athena or Lightstep calls). ``brRef`` across dates uses every date that has an
mdrmfe export in --drm-dir (or --dates). Writes <base>/<OPCO>/<date>_mdrm_devices.md and one Widevine chart under charts/.

Usage:
  python investigations/ctap-smvod/scripts/analyze_mdrm_devices.py --opco ZA --date 2026-10-23 [--min-volume 5]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.drm_devices import (
    DIMENSIONS, GroupStat, br_ref_by_date, br_ref_by_drm_type, device_split, outcome_by_kind, rank_failures,
    widevine_hd_loss, widevine_level_br_ref,
)
from lib.drm_exports import export_dates, read_cdm, read_lrm, read_mdrmfe
from src.lib.charts.errors import ChartError
from src.lib.charts.output import write_chart_png
from src.lib.charts.stacked_bar import render_stacked_bar

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_mdrm_devices")
DEFAULT_BASE = Path(__file__).resolve().parents[1] / "output"
DEFAULT_DRM_BASE = Path(__file__).resolve().parents[1] / "data" / "lightstep"
TOP_N = 15


def pct(part: int, total: int) -> str:
    return f"{100.0 * part / total:.1f}%" if total else "n/a"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(r) + " |" for r in rows)
    return lines


def _stat_rows(stats: list[GroupStat], limit: int = TOP_N) -> list[list[str]]:
    return [[g.key, str(g.requests), str(g.failures), pct(g.failures, g.requests)] for g in stats[:limit]] or [["none", "", "", ""]]


def _pivot(data: dict[str, dict[str, int]], first: str) -> list[str]:
    cols = sorted({c for per in data.values() for c in per})
    return _table([first, *cols, "total"],
                  [[k, *(str(per.get(c, 0)) for c in cols), str(sum(per.values()))] for k, per in data.items()])


def chart_filename(date: str) -> str:
    return f"{date}_mdrm_widevine_level_brref.png"


def write_chart(base: Path, opco: str, date: str, levels: dict[str, dict[str, int]], total: int) -> str:
    """Returns the chart file name, or ``""`` when there is nothing to plot or drawing failed (logged)."""
    if not levels:
        return ""
    brs = sorted({b for per in levels.values() for b in per})
    labels = list(levels)
    series = {b: [levels[lvl].get(b, 0) for lvl in labels] for b in brs}
    try:
        png = render_stacked_bar(labels, series, title="Widevine requests by security level and brRef",
                                 subtitle=f"{opco} {date} · {total} requests", total=total)
    except ChartError as exc:
        LOGGER.error("%s %s: widevine chart failed: %s", opco, date, exc)
        return ""
    write_chart_png(png, base, opco, chart_filename(date))
    return chart_filename(date)


def render_markdown(opco: str, date: str, drm_dir: Path, dates: list[str], min_volume: int, chart: str = "") -> str:
    mdrmfe, lrm, cdm = read_mdrmfe(drm_dir, date), read_lrm(drm_dir, date), read_cdm(drm_dir, date)
    loss = widevine_hd_loss(mdrmfe, cdm)
    lines = [f"# mDRM device and policy report — {opco} — {date}", ""]
    if chart:
        lines += [f"![widevine level brRef](charts/{chart})", ""]
    lines += ["## brRef per DRM type", ""] + _pivot(br_ref_by_drm_type(mdrmfe), "drm_type")
    lines += ["", "## Widevine security level vs brRef", ""] + _pivot(widevine_level_br_ref(mdrmfe, cdm), "security_level")
    lines += ["", f"**HD loss:** {loss.l1_low_requests} of {loss.widevine_requests} Widevine requests "
                  f"({pct(loss.l1_low_requests, loss.widevine_requests)}) and {loss.l1_low_sessions} of "
                  f"{loss.widevine_sessions} Widevine sessions ({pct(loss.l1_low_sessions, loss.widevine_sessions)}) are L1 "
                  "devices that got `brRef=LOW` (SD only). FairPlay and PlayReady are excluded: they have no L1/L3 split, "
                  "so `LOW` there is the likely default, not a downgrade."]
    for title, kind in (("FairPlay devices (type / OS)", "fairplay"), ("PlayReady devices", "playready")):
        lines += ["", f"## {title}", ""] + _table(["device", "requests", "failures", "failure rate"],
                                                    _stat_rows(device_split(mdrmfe, lrm, cdm, kind)))
    lines += ["", "## License outcome by VOD vs linear (sessions)", ""] + _pivot(outcome_by_kind(mdrmfe, lrm), "kind")
    for dim in DIMENSIONS:
        lines += ["", f"## Failing {dim}s (at least {min_volume} requests)", ""]
        lines += _table([dim, "requests", "failures", "failure rate"], _stat_rows(rank_failures(mdrmfe, lrm, cdm, dim, min_volume)))
    per_date, constant = br_ref_by_date({d: read_mdrmfe(drm_dir, d) for d in dates})
    lines += ["", "## brRef across dates", ""] + _pivot(per_date, "date")
    lines += ["", "`brRef` is constant across these dates." if constant else "`brRef` varies across these dates."]
    return "\n".join(lines) + "\n"


def run(opco: str, date: str, base: Path, drm_dir: Path, min_volume: int = 5, dates: list[str] | None = None) -> Path:
    mdrmfe, cdm = read_mdrmfe(drm_dir, date), read_cdm(drm_dir, date)
    levels = widevine_level_br_ref(mdrmfe, cdm)
    chart = write_chart(base, opco, date, levels, widevine_hd_loss(mdrmfe, cdm).widevine_requests)
    text = render_markdown(opco, date, drm_dir, dates or export_dates(drm_dir), min_volume, chart)
    out = base / opco
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{date}_mdrm_devices.md"
    path.write_text(text, encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder, e.g. ZA")
    ap.add_argument("--date", required=True, help="day YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--drm-dir", type=Path, default=None, help="folder with the saved mDRM exports (default data/lightstep/<OPCO>)")
    ap.add_argument("--min-volume", type=int, default=5, help="hide groups with fewer requests (default 5)")
    ap.add_argument("--dates", nargs="*", default=None, help="dates for the brRef-across-dates table (default: all with an mdrmfe export)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-analyze_mdrm_devices")
    args = parse_args(argv)
    path = run(args.opco, args.date, args.base, args.drm_dir or DEFAULT_DRM_BASE / args.opco, args.min_volume, args.dates)
    LOGGER.info("%s %s: wrote %s", args.opco, args.date, path)


if __name__ == "__main__":
    main()
