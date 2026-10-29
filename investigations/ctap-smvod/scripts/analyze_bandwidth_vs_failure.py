#!/usr/bin/env python3
"""Does low bandwidth explain playback failures? Summarise `<date>_session_bandwidth.csv` (`run_athena_session_bandwidth.py`).

Writes to `output/<T>/bandwidth/`:
- `<date>_bandwidth_by_errorcode.csv`   per first-error code: sessions, bandwidth coverage and spread (p10/p50/p90, IQR), BUFFERING events,
  Spearman correlation of bandwidth vs BUFFERING, bandwidth headroom over the stream bitrate, and a final healthy-baseline row
- `<date>_abr_failure_rate.csv`         share of sessions with an error per ABR-bitrate bucket (the only healthy-session bandwidth proxy)
- `<date>_bandwidth_stats.csv`          overall tests: Spearman (all error sessions) and Mann-Whitney (error vs healthy ABR bitrate)
- `<date>_effectivetype_by_errorcode.csv`  navigator.connection effective network type per error code

Usage:
    python3 analyze_bandwidth_vs_failure.py --date 2026-10-24 --tenant ZA
"""
import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.bandwidth_stats import (
    abr_error_vs_healthy, failure_rate_by_abr_bucket, group_by_errorcode, healthy_sessions, is_true, overall_bandwidth_vs_buffering, summarize_code,
)
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_bandwidth_vs_failure")
INVESTIGATION_DIR = Path(__file__).resolve().parent.parent
REQUIRED = {"sessionid", "has_error", "first_errorcode", "est_bw_mbps_max", "stream_bw_mbps", "buffering_events",
            "buf_cur_last", "abr_bitrate_mbps_avg", "nav_effectivetype"}


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def by_errorcode_table(rows: Sequence[Mapping[str, str]]) -> list[dict]:
    """Pure: one summary row per first-error code, largest first, plus a healthy-session baseline row (buffering comparison)."""
    groups = group_by_errorcode(rows)
    table = [{"errorcode": code, **summarize_code(g)} for code, g in sorted(groups.items(), key=lambda kv: -len(kv[1]))]
    return table + [{"errorcode": "(healthy baseline)", **summarize_code(healthy_sessions(rows))}]


def effectivetype_table(rows: Sequence[Mapping[str, str]]) -> list[dict]:
    """Pure: sessions per (errorcode, navigator.connection effectivetype); a blank type is reported as 'unknown'."""
    counts = Counter(
        (code, (r.get("nav_effectivetype") or "").strip() or "unknown")
        for code, g in group_by_errorcode(rows).items() for r in g
    )
    return [{"errorcode": c, "effectivetype": t, "sessions": n} for (c, t), n in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1]))]


def stats_table(rows: Sequence[Mapping[str, str]]) -> list[dict]:
    """Pure: the overall tests as name/value rows."""
    overall = overall_bandwidth_vs_buffering(rows)
    abr = abr_error_vs_healthy(rows)
    return [
        {"stat": "error_sessions", "value": sum(is_true(r.get("has_error")) for r in rows)},
        {"stat": "healthy_sessions", "value": sum(not is_true(r.get("has_error")) for r in rows)},
        {"stat": "spearman_bw_vs_buffering_n", "value": overall["n"]},
        {"stat": "spearman_bw_vs_buffering", "value": overall["spearman"]},
        *({"stat": f"abr_{k}", "value": v} for k, v in abr.items()),
    ]


def write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"nothing to write to {path}")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if v is None else (round(v, 4) if isinstance(v, float) else v)) for k, v in row.items()})


def main() -> None:
    init_logging("ctap-smvod-analyze_bandwidth_vs_failure")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", required=True, help="Tenant folder (e.g. ZA)")
    ap.add_argument("--input", default=None, help="Override the input CSV (default: data/athena/<T>/<date>_session_bandwidth.csv)")
    ap.add_argument("--output-dir", default=None, help="Override the output folder (default: output/<T>/bandwidth)")
    args = ap.parse_args()

    src = Path(args.input) if args.input else INVESTIGATION_DIR / "data" / "athena" / args.tenant / f"{args.date}_session_bandwidth.csv"
    out = Path(args.output_dir) if args.output_dir else INVESTIGATION_DIR / "output" / args.tenant / "bandwidth"
    try:
        rows = read_rows(src)
        outputs = {
            f"{args.date}_bandwidth_by_errorcode.csv": by_errorcode_table(rows),
            f"{args.date}_abr_failure_rate.csv": failure_rate_by_abr_bucket(rows),
            f"{args.date}_bandwidth_stats.csv": stats_table(rows),
            f"{args.date}_effectivetype_by_errorcode.csv": effectivetype_table(rows),
        }
        for name, table in outputs.items():
            write_csv(out / name, table)
            print(f"wrote {out / name} ({len(table)} rows)", file=sys.stderr)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    LOGGER.info("Completed analyze_bandwidth_vs_failure sessions=%d out=%s", len(rows), out)


if __name__ == "__main__":
    main()
