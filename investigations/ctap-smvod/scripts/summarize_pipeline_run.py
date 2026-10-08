#!/usr/bin/env python3
"""Reconcile one tenant/date pipeline run: Lightstep export row counts vs the merged report.

Prints a markdown summary (export rows and distinct trace ids, trace overlap, merged rows, match
statuses, error-code token distribution, outcome match) so a pilot run can be recorded without ad hoc
analysis. Reads existing files only.

Usage:
    python3 summarize_pipeline_run.py --date 01102026 --tenant ZM
    python3 summarize_pipeline_run.py --date 01102026 --tenant SA
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

TRACE_KEY = "lightstep.trace_id"
EXPORTS = ("ctap", "smvod", "smvod-ts")
MERGED_COLUMNS = ("match_status", "outcome_match_status", "playback_outcome", "error_codes")
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV (BOM-tolerant); a missing file raises FileNotFoundError."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def error_token_counts(rows: list[dict[str, str]]) -> Counter:
    """Count each error code once per session row (tokens split on ';' or ',')."""
    counts: Counter = Counter()
    for row in rows:
        raw = (row.get("error_codes") or "").replace(";", ",")
        counts.update({t.strip() for t in raw.split(",") if t.strip()})
    return counts


def require_columns(rows: list[dict[str, str]], columns: tuple[str, ...], source: str) -> None:
    """Fail loudly when a non-empty CSV lacks a column the summary depends on."""
    missing = [c for c in columns if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{source} is missing required column(s): {missing}")


def trace_ids(rows: list[dict[str, str]]) -> set[str]:
    return {r[TRACE_KEY] for r in rows if r.get(TRACE_KEY)}


def render(tenant: str, iso_date: str, exports: dict[str, list[dict[str, str]]], merged: list[dict[str, str]]) -> str:
    ctap, smvod = trace_ids(exports["ctap"]), trace_ids(exports["smvod"])
    lines = [f"## {tenant} {iso_date}", "", "| Export | Rows | Distinct trace ids |", "|---|---|---|"]
    for name, rows in exports.items():
        lines.append(f"| {name} | {len(rows)} | {len(trace_ids(rows)) if rows and TRACE_KEY in rows[0] else 'n/a'} |")
    lines += ["", f"- ctap ∩ smvod traces: {len(ctap & smvod)}; ctap only: {len(ctap - smvod)}; smvod only: {len(smvod - ctap)}",
              f"- merged rows: {len(merged)} (ctap ∪ smvod = {len(ctap | smvod)})"]
    for col in ("match_status", "outcome_match_status", "playback_outcome"):
        lines.append(f"- {col}: {dict(Counter(r.get(col, '') or '(blank)' for r in merged))}")
    with_err = [r for r in merged if (r.get("error_codes") or "").strip()]
    lines += [f"- sessions with error codes: {len(with_err)} of {len(merged)}", "", "| Error code | Sessions |", "|---|---|"]
    lines += [f"| {code} | {n} |" for code, n in error_token_counts(merged).most_common()]
    return "\n".join(lines)


def main() -> int:
    init_logging("ctap-smvod-summarize_pipeline_run")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="DDMMYYYY")
    ap.add_argument("--tenant", required=True, help="Tenant code, e.g. ZM")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Investigation root (default: ctap-smvod)")
    args = ap.parse_args()
    iso = datetime.strptime(args.date, "%d%m%Y").strftime("%Y-%m-%d")
    try:
        exports = {n: read_rows(args.root / "data" / "lightstep" / args.tenant / f"{iso}_{n}.csv") for n in EXPORTS}
        merged = read_rows(args.root / "output" / args.tenant / f"{iso}_setupsession_with_outcome.csv")
        for name in ("ctap", "smvod"):
            require_columns(exports[name], (TRACE_KEY,), f"{name} export")
        require_columns(merged, MERGED_COLUMNS, "merged report")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(render(args.tenant, iso, exports, merged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
