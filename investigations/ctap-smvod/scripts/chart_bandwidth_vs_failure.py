#!/usr/bin/env python3
"""Charts for the bandwidth-vs-playback-failure analysis, from `<date>_session_bandwidth.csv` (`run_athena_session_bandwidth.py`).

Writes five PNGs to `output/<T>/charts/` (`src/lib/charts` dark theme):
- `<date>_bw_spread_by_errorcode.png`     box plot of Shaka's estimated bandwidth per first-error code (the spread)
- `<date>_bw_coverage_by_errorcode.png`   share of each code's sessions that logged a bandwidth estimate at all
- `<date>_buffering_vs_healthy.png`       average BUFFERING events per code against the healthy-session baseline
- `<date>_bw_vs_buffering_scatter.png`    one dot per error session: bandwidth vs BUFFERING events
- `<date>_abr_error_rate.png`             share of sessions with an error per ABR-bitrate bucket (healthy-session proxy, small sample)

Usage:
    python3 chart_bandwidth_vs_failure.py --date 2026-10-24 --tenant ZA
"""
import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Mapping, Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.bandwidth_stats import (
    MIN_N, bandwidth, failure_rate_by_abr_bucket, group_by_errorcode, healthy_sessions, num, spearman, summarize_code,
)
from src.lib.charts.errors import ChartError
from src.lib.charts.fig import new_figure, render_png
from src.lib.charts.output import write_chart_png
from src.lib.charts.shapes import add_bars
from src.lib.charts.theme import DARK, ChartTheme, chart_font_family
from src.lib.logging.bootstrap import init_logging
from src.lib.charts.axes import style_axes

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.chart_bandwidth_vs_failure")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "athena"
HEIGHT = 5.2


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _canvas(title: str, subtitle: str, theme: ChartTheme):
    family = chart_font_family()
    fig = new_figure(theme, HEIGHT)
    fig.subplots_adjust(left=0.12, bottom=0.17, top=0.8)
    fig.text(0.12, 0.93, title, color=theme.ink, fontsize=13, fontweight="bold", family=family)
    fig.text(0.12, 0.88, subtitle, color=theme.muted, fontsize=8.5, family=family)
    ax = fig.add_subplot(111)
    return fig, ax, family


def _finish(fig, ax, theme: ChartTheme, family: str, footnote: str) -> bytes:
    style_axes(ax, theme, family)
    fig.text(0.12, 0.02, footnote, color=theme.muted, fontsize=7.5, family=family)
    return render_png(fig, theme)


def _rounded_bars(ax, labels: Sequence[str], vals: Sequence[float], colours, theme: ChartTheme) -> list[int]:
    """Rounded vertical bars at integer positions with ``labels`` as ticks; the caller sets the y range."""
    positions = list(range(len(labels)))
    add_bars(ax, positions, vals, colours, theme.corner_radius_in)
    ax.set_xticks(positions, labels)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(0, max(max(vals), 1e-9) * 1.18)
    return positions


def bandwidth_samples(rows: Sequence[Mapping[str, str]], min_n: int = MIN_N) -> dict[str, list[float]]:
    """Pure: bandwidth estimates per first-error code, keeping only codes with at least ``min_n`` values."""
    out = {code: [b for b in (bandwidth(r) for r in g) if b is not None] for code, g in group_by_errorcode(rows).items()}
    return {c: v for c, v in sorted(out.items(), key=lambda kv: -len(kv[1])) if len(v) >= min_n}


def render_spread(rows: Sequence[Mapping[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    """Box plot (log y) of estimated bandwidth per error code with n labels; raises ChartError when no code has enough values."""
    try:
        samples = bandwidth_samples(rows)
        if not samples:
            raise ValueError(f"no error code has {MIN_N}+ bandwidth values")
        fig, ax, family = _canvas("Bandwidth spread at the moment of failure", title, theme)
        box = ax.boxplot(list(samples.values()), whis=(10, 90), showfliers=False, patch_artist=True, widths=0.55)
        for patch in box["boxes"]:
            patch.set(facecolor=theme.series[0], alpha=0.5, edgecolor=theme.series[0])
        for part in ("medians",):
            for line in box[part]:
                line.set(color=theme.amber, lw=2)
        for part in ("whiskers", "caps"):
            for line in box[part]:
                line.set(color=theme.muted)
        ax.set_yscale("log")
        ax.set_xticks(range(1, len(samples) + 1), [f"{c}\nn={len(v)}" for c, v in samples.items()])
        ax.set_ylabel("Estimated bandwidth (Mbps, log scale)", color=theme.muted, fontsize=9)
        return _finish(fig, ax, theme, family, "Box = middle 50% of sessions, line = median, whiskers = 10th-90th percentile. Codes with <5 readings omitted.")
    except Exception as exc:  # noqa: BLE001 - boundary: nothing but ChartError escapes
        raise ChartError(f"bandwidth spread chart failed: {exc}") from exc


def render_coverage(rows: Sequence[Mapping[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    try:
        groups = {c: g for c, g in group_by_errorcode(rows).items() if len(g) >= MIN_N}
        if not groups:
            raise ValueError("no error code has enough sessions")
        stats = {c: summarize_code(g) for c, g in groups.items()}
        fig, ax, family = _canvas("How many failing sessions have a bandwidth reading?", title, theme)
        labels = [f"{c}\nn={s['sessions']}" for c, s in stats.items()]
        vals = [s["coverage_pct"] for s in stats.values()]
        for x, v in zip(_rounded_bars(ax, labels, vals, theme.series[0], theme), vals):
            ax.text(x, v + 1.5, f"{v:.0f}%", ha="center", color=theme.ink, fontsize=9, family=family)
        ax.set_ylim(0, 110)
        ax.set_ylabel("% of sessions with a bandwidth estimate", color=theme.muted, fontsize=9)
        return _finish(fig, ax, theme, family, "Codes at 0% fail before downloading starts, so bandwidth cannot explain them either way.")
    except Exception as exc:  # noqa: BLE001
        raise ChartError(f"bandwidth coverage chart failed: {exc}") from exc


def render_buffering(rows: Sequence[Mapping[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    try:
        groups = {c: g for c, g in group_by_errorcode(rows).items() if len(g) >= MIN_N}
        healthy = healthy_sessions(rows)
        if not groups or not healthy:
            raise ValueError("need error codes with enough sessions and healthy sessions")
        avgs = {c: summarize_code(g)["avg_buffering_events"] for c, g in groups.items()}
        base = summarize_code(healthy)["avg_buffering_events"]
        fig, ax, family = _canvas("Buffering: failing sessions vs healthy sessions", title, theme)
        labels = [f"{c}\nn={len(groups[c])}" for c in avgs] + [f"healthy\nn={len(healthy)}"]
        vals = list(avgs.values()) + [base]
        colors = [theme.red if v > base else theme.series[0] for v in avgs.values()] + [theme.green]
        for x, v in zip(_rounded_bars(ax, labels, vals, colors, theme), vals):
            ax.text(x, v + 0.4, f"{v:.1f}", ha="center", color=theme.ink, fontsize=9, family=family)
        ax.axhline(base, color=theme.green, lw=1, ls="--")
        ax.set_ylabel("Average BUFFERING events per session", color=theme.muted, fontsize=9)
        return _finish(fig, ax, theme, family, "Red = more buffering than the healthy average (dashed line). Buffering is common in healthy sessions too.")
    except Exception as exc:  # noqa: BLE001
        raise ChartError(f"buffering chart failed: {exc}") from exc


def render_scatter(rows: Sequence[Mapping[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    try:
        groups = group_by_errorcode(rows)
        points = {c: [(b, num(r.get("buffering_events")) or 0.0) for r in g if (b := bandwidth(r)) is not None and b > 0] for c, g in groups.items()}
        points = {c: p for c, p in points.items() if p}
        if not points:
            raise ValueError("no error session has a bandwidth estimate")
        every = [p for pts in points.values() for p in pts]
        rho = spearman([p[0] for p in every], [p[1] for p in every])
        fig, ax, family = _canvas("Bandwidth vs buffering, per failing session", title, theme)
        for color, (code, pts) in zip(list(theme.series) + [theme.amber, theme.red], points.items()):
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=16, alpha=0.7, color=color, label=f"{code} (n={len(pts)})", linewidths=0)
        ax.set_xscale("log")
        ax.set_xlabel("Estimated bandwidth (Mbps, log scale)", color=theme.muted, fontsize=9)
        ax.set_ylabel("BUFFERING events in the session", color=theme.muted, fontsize=9)
        ax.legend(frameon=False, labelcolor=theme.muted, fontsize=8)
        note = f"Spearman rho = {rho:.2f} (n={len(every)}). Near 0 = no link, -1 = lower bandwidth always means more buffering." if rho is not None else "Too few points for a correlation."
        return _finish(fig, ax, theme, family, note)
    except Exception as exc:  # noqa: BLE001
        raise ChartError(f"bandwidth scatter chart failed: {exc}") from exc


def render_abr_rate(rows: Sequence[Mapping[str, str]], title: str, theme: ChartTheme = DARK) -> bytes:
    try:
        table = failure_rate_by_abr_bucket(rows)
        if not any(r["sessions"] for r in table):
            raise ValueError("no session has ABR bitrate data")
        fig, ax, family = _canvas("Error rate by ABR bitrate (healthy-session proxy)", title, theme)
        labels = [f"{r['abr_bucket_mbps']} Mbps\nn={r['sessions']}" for r in table]
        vals = [r["error_rate_pct"] or 0.0 for r in table]
        for x, v in zip(_rounded_bars(ax, labels, vals, theme.series[1], theme), vals):
            ax.text(x, v + 1, f"{v:.0f}%", ha="center", color=theme.ink, fontsize=9, family=family)
        ax.set_ylim(0, max(vals + [10]) * 1.2)
        ax.set_ylabel("% of sessions with an error", color=theme.muted, fontsize=9)
        return _finish(fig, ax, theme, family, "Only sessions that logged a track change (a small sample): indicative, not conclusive.")
    except Exception as exc:  # noqa: BLE001
        raise ChartError(f"ABR error-rate chart failed: {exc}") from exc


CHARTS = (
    ("bw_spread_by_errorcode", render_spread),
    ("bw_coverage_by_errorcode", render_coverage),
    ("buffering_vs_healthy", render_buffering),
    ("bw_vs_buffering_scatter", render_scatter),
    ("abr_error_rate", render_abr_rate),
)


def write_charts(tenant: str, date_iso: str, output_dir: Path = OUTPUT_DIR, data_dir: Path = DATA_DIR) -> bool:
    """Writes every PNG; a ChartError is logged, returns False, and the other charts still run."""
    rows = read_rows(data_dir / tenant / f"{date_iso}_session_bandwidth.csv")
    sessions = len(rows)
    title = f"{tenant}, {date_iso} (UTC), {sessions} sessions"
    ok = True
    for suffix, render in CHARTS:
        try:
            png = render(rows, title)
        except ChartError:
            LOGGER.exception("%s: chart %s failed", tenant, suffix)
            ok = False
            continue
        LOGGER.info("%s: wrote %s", tenant, write_chart_png(png, output_dir, tenant, f"{date_iso}_{suffix}.png"))
    return ok


def main() -> None:
    init_logging("ctap-smvod-chart_bandwidth_vs_failure")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", required=True, help="Tenant folder (e.g. ZA)")
    args = ap.parse_args()
    try:
        ok = write_charts(args.tenant, args.date)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
