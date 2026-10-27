"""POC: bandwidth bands per error code for VSF-T sessions (ZA error summary preview).

Purpose: for each VSF-T session (first error, as in the VSF-T POC), band Shaka estimatedbandwidth
(est_bandwidth_mbps in the flattened eventdata) and print markdown rows per code, with a 'no data' row.

Args:
    --tenant   Tenant identifier.
    --date     Date (YYYY-MM-DD).
    --flat     Flattened eventdata CSV (flatten_error_eventdata.py `<date>_all.csv`).
    --codes    Comma-separated error codes to report (default 6001,3016,1003,E31012).
"""
import argparse
import csv
import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANDS = [("under 1 Mbps", 0, 1), ("1 to 3 Mbps", 1, 3), ("3 to 10 Mbps", 3, 10), ("over 10 Mbps", 10, float("inf"))]


def load_poc():
    spec = importlib.util.spec_from_file_location("poc", Path(__file__).with_name("2026-10-27_conviva-vsf-technical_timeseries_poc.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def band(value: str) -> str:
    if not value:
        return "no data"
    v = float(value)
    if not v >= 0:
        return "no data"
    return next(name for name, lo, hi in BANDS if lo <= v < hi)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--flat", type=Path, required=True)
    ap.add_argument("--codes", default="6001,3016,1003,E31012")
    args = ap.parse_args()
    poc = load_poc()
    sessions = poc.read_sessions(poc.DATA / "athena" / args.tenant / f"{args.date}_debug_all_events.csv")
    vsf = {s for s, ev in sessions.items() if (t := poc.create_time(ev)) and t.date().isoformat() == args.date and poc.start_failure(ev)}
    first: dict[str, dict] = {}
    with args.flat.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            s = r["sessionId"]
            if s in vsf and (s not in first or r["datetime"] < first[s]["datetime"]):
                first[s] = r
    for code in [c.strip() for c in args.codes.split(",")]:
        rows = [r for r in first.values() if r["errorcode"] == code]
        if not rows:
            raise SystemExit(f"no VSF-T sessions with first error {code}")
        counts = Counter(band(r["est_bandwidth_mbps"]) for r in rows)
        vals = sorted(v for v in (float(r["est_bandwidth_mbps"] or "nan") for r in rows) if v >= 0)
        med = f"p50 {vals[len(vals) // 2]:.1f} / p90 {vals[-(-9 * len(vals) // 10) - 1]:.1f} (n={len(vals)})" if vals else "n/a"
        print(f"\n{code} sessions={len(rows)} est_bandwidth {med}")
        for name in [b[0] for b in BANDS] + ["no data"]:
            print(f"  {name}: {counts.get(name, 0)} ({100 * counts.get(name, 0) / len(rows):.1f}%)")


if __name__ == "__main__":
    main()
