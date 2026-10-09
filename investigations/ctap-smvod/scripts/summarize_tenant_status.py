#!/usr/bin/env python3
"""Cross-tenant daily playback status summary (markdown) from the merged pipeline reports.

Reads `output/<TENANT>/YYYY-MM-DD_setupsession_with_outcome.csv` for each tenant, deduplicates rows by
sessionId (rows with a blank sessionId, i.e. ctap-only traces with no SM-VOD session, are dropped) and writes `docs/YYYY-MM-DD-tenant-status-summary.md`:
headline "played OK" proxy, outcomes, error codes and caveats. The day is UTC. INCOMPLETE_NO_DESTROY is
deliberately left out of the outcome table (ambiguous bucket, see
knowledge/mtn-adoption-playback-outcome-classification-gap.md). Takeaways are judgement, so write them by hand.

Usage:
    python3 summarize_tenant_status.py --date 08102026
    python3 summarize_tenant_status.py --date 08102026 --tenants SA,GH,ZM --out /tmp/summary.md
"""
import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TENANTS = ("SA", "GH", "ZM")
REQUIRED_COLUMNS = ("sessionId", "deviceId", "householdId", "playback_outcome", "error_codes", "state_sequence",
                    "position_not_moved", "startup_time_ms", "Device Class")
SHOWN_OUTCOMES = ("DESTROY", "TIMEOUT", "EBVS", "PLAYER_ERROR")
MAX_CODE_ROWS = 8


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV (BOM-tolerant); a missing file raises FileNotFoundError."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def require_columns(rows: list[dict[str, str]], source: str) -> None:
    """Fail loudly when a non-empty report lacks a column the summary depends on."""
    missing = [c for c in REQUIRED_COLUMNS if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{source} is missing required column(s): {missing}")


def dedupe_sessions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop rows with a blank sessionId (ctap-only traces); keep the first row per sessionId (a repeated id never differs in practice)."""
    seen: set[str] = set()
    out = []
    for row in rows:
        sid = (row.get("sessionId") or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(row)
    return out


def error_codes_of(row: dict[str, str]) -> set[str]:
    return {t.strip() for t in re.split(r"[;,|]", row.get("error_codes") or "") if t.strip()}


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile (q in 0..1); None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def startup_values(sessions: list[dict[str, str]]) -> list[float]:
    vals = []
    for row in sessions:
        try:
            vals.append(float(row["startup_time_ms"]))
        except (KeyError, TypeError, ValueError):
            continue
    return vals


def tenant_metrics(rows: list[dict[str, str]]) -> dict:
    """Session-level metrics for one tenant (pure; `rows` is the merged report)."""
    sessions = dedupe_sessions(rows)
    errored = [r for r in sessions if error_codes_of(r)]
    played = lambda r: "PLAYING" in (r.get("state_sequence") or "")  # noqa: E731
    ok = sum(1 for r in sessions if played(r) and not error_codes_of(r))
    top_devices = Counter(r["deviceId"] for r in errored if r.get("deviceId")).most_common(4)
    classes = Counter(r["Device Class"] for r in sessions if r.get("Device Class"))
    startup = startup_values(sessions)
    return {
        "sessions": len(sessions),
        "devices": len({r["deviceId"] for r in sessions if r.get("deviceId")}),
        "households": len({r["householdId"] for r in sessions if r.get("householdId")}),
        "ok": ok,
        "errored": len(errored),
        "neither": len(sessions) - ok - len(errored),
        "errored_pre_play": sum(1 for r in errored if not played(r)),
        "top4_error_devices": sum(n for _, n in top_devices),
        "pos_not_moved": sum(1 for r in sessions if (r.get("position_not_moved") or "").strip().lower() == "true"),
        "startup_p50": percentile(startup, 0.5),
        "startup_p75": percentile(startup, 0.75),
        "main_class": classes.most_common(1)[0] if classes else None,
        "outcomes": Counter((r.get("playback_outcome") or "").strip() for r in sessions),
        "codes": Counter(c for r in sessions for c in error_codes_of(r)),
    }


def pct(n: int, total: int) -> str:
    if total == 0:
        return "n/a"
    p = 100 * n / total
    return "<1%" if 0 < p < 1 else f"{round(p)}%"


def cell(n: int, total: int) -> str:
    return f"{n:,} ({pct(n, total)})"


def seconds(ms: float | None) -> str:
    return "n/a" if ms is None else f"{ms / 1000:.1f} s"


def code_columns(metrics: dict[str, dict]) -> tuple[list[str], int]:
    """Top codes by total sessions across tenants, capped at MAX_CODE_ROWS."""
    totals: Counter = Counter()
    for m in metrics.values():
        totals.update(m["codes"])
    ranked = [c for c, _ in totals.most_common()]
    return ranked[:MAX_CODE_ROWS], len(ranked)


def render(iso_date: str, metrics: dict[str, dict]) -> str:
    tenants = list(metrics)
    head = "| " + " | ".join([""] + tenants) + " |\n|" + "---|" * (len(tenants) + 1)

    def row(label: str, fn) -> str:
        return "| " + " | ".join([label] + [fn(metrics[t]) for t in tenants]) + " |"

    out = [f"# Tenant playback status summary — {iso_date} ({', '.join(tenants)})", "",
           "Built by `scripts/summarize_tenant_status.py` from `output/<TENANT>/…_setupsession_with_outcome.csv`; rows without a "
           "`sessionId` (ctap-only traces) are dropped. Day is UTC. **Played OK** = the session's `state_sequence` reached `PLAYING` and it carries no error code "
           "(a proxy, not an official success rate).", "", "## Headline", "", head,
           row("Playback sessions", lambda m: f"{m['sessions']:,}"),
           row("Devices / households", lambda m: f"{m['devices']:,} / {m['households']:,}"),
           row("**Played OK**", lambda m: f"**{cell(m['ok'], m['sessions'])}**"),
           row("Failed with an error code", lambda m: cell(m["errored"], m["sessions"])),
           row("Neither played nor errored", lambda m: cell(m["neither"], m["sessions"])),
           row("Error sessions that never reached PLAYING", lambda m: f"{m['errored_pre_play']:,} of {m['errored']:,} ({pct(m['errored_pre_play'], m['errored'])})"),
           row("Top 4 devices' share of error sessions", lambda m: pct(m["top4_error_devices"], m["errored"])),
           row("Playback position never advanced", lambda m: pct(m["pos_not_moved"], m["sessions"])),
           row("Startup median / p75", lambda m: f"{seconds(m['startup_p50'])} / {seconds(m['startup_p75'])}"),
           row("Main device class", lambda m: f"{m['main_class'][0]} {pct(m['main_class'][1], m['sessions'])}" if m["main_class"] else "n/a"),
           "", "## Playback outcome (share of all sessions)", "",
           "`INCOMPLETE_NO_DESTROY` and sessions with no Athena outcome are omitted, so columns do not sum to 100%.", "", head]
    out += [row(o, lambda m, o=o: cell(m["outcomes"].get(o, 0), m["sessions"])) for o in SHOWN_OUTCOMES]
    codes, n_codes = code_columns(metrics)
    out += ["", "## Error codes (sessions, % of the tenant's sessions)", "", head]
    out += [row(c, lambda m, c=c: cell(m["codes"].get(c, 0), m["sessions"])) for c in codes]
    if n_codes > len(codes):
        out.append(row("Other", lambda m: f"{sum(n for c, n in m['codes'].items() if c not in codes):,}"))
    out += [row("**Sessions with any error**", lambda m: f"**{cell(m['errored'], m['sessions'])}**"), "",
            "A session can carry several codes, so rows can slightly exceed the \"any error\" total.", "",
            "## Caveats", "",
            "- Single day; small tenants' percentages move a lot with a few sessions.",
            "- Sessions with no Athena outcome: " + ", ".join(
                f"{t} {metrics[t]['outcomes'].get('', 0):,} ({pct(metrics[t]['outcomes'].get('', 0), metrics[t]['sessions'])})" for t in tenants) + ".",
            "- VSF (viewing start failure) is not measurable from this export; `state_sequence` is only a proxy for failure before playback.",
            "- Takeaways are not generated; add them by hand."]
    return "\n".join(out) + "\n"


def default_out(root: Path, iso_date: str) -> Path:
    return root / "docs" / f"{iso_date}-tenant-status-summary.md"


def main() -> int:
    init_logging("ctap-smvod-summarize_tenant_status")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="DDMMYYYY (UTC day)")
    ap.add_argument("--tenants", default=",".join(DEFAULT_TENANTS), help="Comma-separated tenant codes (default: SA,GH,ZM)")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Investigation root (default: ctap-smvod)")
    ap.add_argument("--out", type=Path, default=None, help="Output markdown path (default: docs/YYYY-MM-DD-tenant-status-summary.md)")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = ap.parse_args()
    iso = datetime.strptime(args.date, "%d%m%Y").strftime("%Y-%m-%d")
    out_path = args.out or default_out(args.root, iso)
    if out_path.exists() and not args.force:
        print(f"ERROR: {out_path} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    metrics = {}
    try:
        for tenant in [t.strip() for t in args.tenants.split(",") if t.strip()]:
            path = args.root / "output" / tenant / f"{iso}_setupsession_with_outcome.csv"
            rows = read_rows(path)
            require_columns(rows, str(path))
            metrics[tenant] = tenant_metrics(rows)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not metrics:
        print("ERROR: no tenants given", file=sys.stderr)
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(iso, metrics), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
