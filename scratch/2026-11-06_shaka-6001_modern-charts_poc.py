"""POC v3: self-explanatory, rounded, soft-palette redesign of the 9 shaka-6001 charts.

Run: PYTHONPATH=. python scratch/2026-11-06_shaka-6001_modern-charts_poc.py
Values are hard-coded from the findings doc (scratch only). Output: scratch/tmp/modern_charts/.
Everything is drawn in one full-figure axes measured in inches (y down) so corners stay circular.
"""
from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from src.lib.charts.theme import chart_font_family

OUT = Path("scratch/tmp/modern_charts")
W, H, L = 7.4, 4.6, 0.4
BG, INK, MUTED, FAINT = "#0e1117", "#e5e7eb", "#8b93a3", "#222937"
GOOD, BAD, BAD_SOFT = "#5ec8b4", "#f0877f", "#a8645f"
GOOD_SOFT = "#2f7d70"
BLUE, BLUE_SOFT, VIOLET, VIOLET_SOFT = "#7fa8f5", "#456a9e", "#a99bf0", "#5f5894"
FONT = chart_font_family()


def canvas():
    fig = Figure(figsize=(W, H), dpi=200, facecolor=BG)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    return fig, ax


def txt(ax, x, y, s, size=10, color=INK, weight="normal", ha="left", va="center"):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, family=FONT)


def bar(ax, x, y, w, h, color, z=2):
    r = min(h / 2, w / 2, 0.09)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=color, ec="none", zorder=z))


def frame(ax, title, subtitle, footer):
    txt(ax, L, 0.5, title, 15, INK, "bold", va="center")
    txt(ax, L, 0.88, subtitle, 9.5, MUTED)
    txt(ax, L, H - 0.28, footer, 8, MUTED)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, facecolor=BG)


def on(c):
    return "#0e1117" if c in (GOOD, BAD, BLUE, VIOLET) else INK


# ---------- chart shapes ----------
def hrows(ax, rows, vmax, track=False, inline=None, top=1.45, bottom=3.95, span=5.1):
    """rows: (label, value, colour, value_text). Label above bar, or inline at left if inline=width."""
    pitch = (bottom - top) / len(rows)
    x0 = L + (inline or 0)
    for i, (label, v, c, vt) in enumerate(rows):
        y = top + i * pitch
        by = y if inline else y + 0.3
        bh = min(0.3, pitch * 0.6)
        if inline:
            txt(ax, L, y + bh / 2, label, 9.5, INK)
        else:
            txt(ax, L, y + 0.1, label, 9.5, MUTED)
        if track:
            bar(ax, x0, by, span, bh, FAINT, 1)
        w = max(v / vmax * span, 0.12)
        bar(ax, x0, by, w, bh, c)
        vx = x0 + (span if track else w) + 0.12
        txt(ax, vx, by + bh / 2, vt, 12, INK, "bold")


def vcols(ax, labels, vals, colors, fmt, ymax, sub=None):
    base, top = 3.5, 1.55
    n = len(vals)
    gap = (W - 2 * L) / n
    cw = 0.7
    for i, (lab, v, c) in enumerate(zip(labels, vals, colors)):
        cx = L + gap * (i + 0.5)
        h = v / ymax * (base - top)
        bar(ax, cx - cw / 2, base - h, cw, h, c)
        txt(ax, cx, base - h - 0.17, fmt(v), 11.5, INK, "bold", "center")
        txt(ax, cx, base + 0.2, lab, 9.5, MUTED, ha="center")
        if sub and sub.get(i):
            txt(ax, cx, base + 0.42, sub[i], 8.5, BAD, "bold", "center")


def lineplot(ax, labels, series, lo, hi, ticks, fmt_tick, hl=None):
    """series: (values, colour, end_label, highlight_idx or None)."""
    x0, x1, y0, y1 = L + 0.55, W - 1.55, 3.5, 1.5
    px = lambda i: x0 + (x1 - x0) * i / (len(labels) - 1)
    py = lambda v: y0 + (y1 - y0) * (v - lo) / (hi - lo)
    for t in ticks:
        ax.plot([x0 - 0.1, x1 + 0.1], [py(t)] * 2, color=FAINT, lw=1, zorder=1)
        txt(ax, L, py(t), fmt_tick(t), 8.5, MUTED)
    for i, lab in enumerate(labels):
        txt(ax, px(i), y0 + 0.35, lab, 9.5, MUTED, ha="center")
    for vals, c, end, hi_idx in series:
        xs = [px(i) for i in range(len(vals))]
        ys = [py(v) for v in vals]
        ax.plot(xs, ys, color=c, lw=2.8, solid_capstyle="round", solid_joinstyle="round", zorder=3)
        ax.scatter(xs, ys, s=34, color=c, zorder=4, edgecolors=BG, linewidths=1.5)
        txt(ax, xs[-1] + 0.15, ys[-1], end, 10, c, "bold")
        if hi_idx is not None:
            txt(ax, xs[hi_idx], ys[hi_idx] - 0.22, fmt_tick(vals[hi_idx]), 11, INK, "bold", "center")
    return px, py


# ---------- the nine charts ----------
def webview_share():
    fig, ax = canvas()
    frame(ax, "Non-webview 6001s more than doubled: 2.3% to 5.5%",
          "Share of 6001 errors that came from a client that is not a webview",
          "ZA · 6001 events, 4–5 Nov 2026 · upgrade 4 Nov 16:30 IST · small counts, indicative only")
    hrows(ax, [("Before upgrade · 6 of 264 errors", 2.3, VIOLET_SOFT, "2.3%"),
               ("After upgrade · 47 of 850 errors", 5.5, VIOLET, "5.5%")], 10, track=True)
    save(fig, "webview_share.png")


def pct_stacked():
    fig, ax = canvas()
    frame(ax, "6001 hit 18% of sessions on 5 Nov, up from 12%",
          "Share of playback sessions with at least one 6001 error, per day",
          "ZA · 1–5 Nov 2026 (UTC) · 5 Nov provisional: session file was fetched before the day was complete")
    vals = [12.3, 12.3, 12.1, 15.6, 18.3]
    vcols(ax, ["1 Nov", "2 Nov", "3 Nov", "4 Nov", "5 Nov"], vals,
          [BAD_SOFT] * 3 + [BAD] * 2, lambda v: f"{v:.0f}%", 20, {3: "upgrade"})
    save(fig, "session_error_impact_pct_stacked.png")


def share_6001():
    fig, ax = canvas()
    frame(ax, "6001 is the top error: 61–67% of failing sessions",
          "Share of error sessions whose error was 6001, per day",
          "ZA · 1–5 Nov 2026 (UTC) · the rest are other player errors · 5 Nov provisional")
    lineplot(ax, ["1 Nov", "2 Nov", "3 Nov", "4 Nov", "5 Nov"],
             [([60.9, 60.6, 62.0, 67.2, 62.8], BAD, "6001", 3)], 50, 75, [50, 60, 70],
             lambda v: f"{v:.0f}%")
    save(fig, "session_error_impact_6001_share.png")


def counts():
    fig, ax = canvas()
    frame(ax, "6001 sessions rose 30% while all sessions fell 14%",
          "Daily sessions, indexed so 1 Nov = 100",
          "ZA · 1–5 Nov 2026 (UTC) · 6001: 416 to 539 sessions · all: 3,365 to 2,893 · 5 Nov provisional")
    allv = [3365, 4050, 4098, 3711, 2893]
    bad = [416, 499, 496, 580, 539]
    ix = lambda a: [v / a[0] * 100 for v in a]
    lineplot(ax, ["1 Nov", "2 Nov", "3 Nov", "4 Nov", "5 Nov"],
             [(ix(allv), MUTED, "All sessions  86", None), (ix(bad), BAD, "6001 sessions  130", None)],
             80, 140, [80, 100, 120, 140], lambda v: f"{v:.0f}")
    save(fig, "session_error_impact_counts.png")


def top_models():
    fig, ax = canvas()
    frame(ax, "Two Samsung A-series phones make up 25% of 6001s",
          "Share of all 6001 events by device model (six most common models)",
          "ZA · 1,114 6001 events · top 6 = 40% · 'Unknown' (UA reduction) is a masked bucket")
    items = [("SM-A065F", 144), ("SM-A055F", 135), ("SM-A165F", 52), ("SM-A075F", 45),
             ("SM-A057F", 38), ("SM-A042F", 30)]
    rows = [(n, c / 1114 * 100, BLUE if i < 2 else BLUE_SOFT, f"{c / 1114 * 100:.1f}%")
            for i, (n, c) in enumerate(items)]
    hrows(ax, rows, 14, inline=1.3, top=1.5, bottom=4.0, span=4.6)
    save(fig, "top_models.png")


def recovery():
    fig, ax = canvas()
    frame(ax, "Almost no households recover from a 6001",
          "Share of households that played successfully later the same day after a first 6001",
          "ZA · 4–5 Nov 2026 · only 6 recoveries in total, so the drop is not reliable")
    hrows(ax, [("Before upgrade · 5 of 231 households", 2.2, GOOD_SOFT, "2.2%"),
               ("After upgrade · 1 of 352 households", 0.3, GOOD, "0.3%")], 10, track=True)
    save(fig, "recovery_household_by_period.png")


def tenure_households():
    fig, ax = canvas()
    frame(ax, "95% of households were first seen in the last 30 days",
          "Households grouped by when they first appeared in our session data",
          "ZA · 16,168 households · data starts 1 Oct 2026, so long-standing households also look new")
    segs = [("0–7 days", 6069, BLUE), ("8–30 days", 9368, "#5b86d4"), ("31–90 days", 731, VIOLET)]
    total, span, y, h = 16168, W - 2 * L, 1.9, 0.7
    x = L
    for i, (lab, n, c) in enumerate(segs):
        w = n / total * span - 0.04
        bar(ax, x, y, w, h, c)
        right = i == 2
        tx = x + w if right else x
        ha = "right" if right else "left"
        if not right:
            txt(ax, x + w / 2, y + h / 2, f"{n / total * 100:.0f}%", 14, BG, "bold", "center")
        else:
            txt(ax, tx, y - 0.2, f"{n / total * 100:.0f}%", 11, INK, "bold", ha)
        txt(ax, tx, y + h + 0.3, lab, 9.5, INK, "bold", ha)
        txt(ax, tx, y + h + 0.55, f"{n:,} households", 8.5, MUTED, ha=ha)
        x += w + 0.04
    save(fig, "tenure_households_by_bucket.png")


def tenure_success():
    fig, ax = canvas()
    frame(ax, "65% of sessions fail for households first seen in the last week",
          "Failed playback sessions as a share of all sessions, by when the household first appeared",
          "ZA · 88,373 sessions · 'first seen' starts 1 Oct, so this is not customer age")
    hrows(ax, [("First seen 0–7 days ago · 26,645 sessions", 65.0, BAD, "65%"),
               ("8–30 days ago · 56,489 sessions", 63.6, BAD, "64%"),
               ("31–90 days ago · 5,239 sessions", 33.7, BAD_SOFT, "34%")], 100, track=True)
    save(fig, "tenure_success_by_bucket.png")


def webview_trend():
    fig, ax = canvas()
    frame(ax, "Webview share fell below its pre-upgrade level every day",
          "Daily webview share of 6001 errors, in points above or below the before-upgrade 97.7%",
          "ZA · 4–6 Nov 2026 (IST) · 6 Nov is a partial day · small counts, indicative only")
    vals = [-3.4, -1.3, -7.9]
    px, py = lineplot(ax, ["4 Nov (upgrade)", "5 Nov", "6 Nov (partial)"],
                      [(vals, VIOLET, "", None)], -10, 4, [-10, -5, 0],
                      lambda v: f"{v:+.0f}" if v else "0")
    for i, v in enumerate(vals):
        txt(ax, px(i), py(v) + 0.26, f"{v:+.1f} pp".replace("-", "−"), 11, INK, "bold", "center")
    txt(ax, W - 1.4, py(0), "Before-upgrade level", 8.5, MUTED)
    save(fig, "webview_daily_trend.png")


def main():
    for fn in (webview_share, pct_stacked, share_6001, counts, top_models, recovery,
               tenure_households, tenure_success, webview_trend):
        fn()
    print(f"wrote {len(list(OUT.glob('*.png')))} charts to {OUT}")


if __name__ == "__main__":
    main()
