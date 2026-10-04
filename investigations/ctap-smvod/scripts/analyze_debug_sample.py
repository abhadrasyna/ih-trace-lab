#!/usr/bin/env python3
"""
One-off analysis helper for the broad eventclass='PLAYER' exploration sample
(queries/exploration/debug_events_broad_sample_08072026.csv, produced by the
query in queries/exploration -- see conversation/QUERY_CATALOG.md for the
SQL). Not part of the production pipeline; used to eyeball eventid
distribution, check whether errorcode/errordescription ever populate outside
PLAYER_ERROR rows, and confirm eventdata shapes for a handful of sample
sessionIds before finalizing the full-day errorcode/errordescription
extraction query (QUERY_CATALOG.md §6/§7).

Usage:
    python3 analyze_debug_sample.py \
        --input ../queries/exploration/debug_events_broad_sample_08072026.csv
"""
import argparse
import logging
from lib import csv_io_compat as csv
from collections import Counter
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_debug_sample")


def main():
    init_logging("ctap-smvod-analyze_debug_sample")
    LOGGER.info("Starting analyze_debug_sample")
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    print("total rows:", len(rows))

    print("\neventid distribution:")
    c = Counter(r["eventid"] for r in rows)
    for k, v in c.most_common():
        print(f"  {v:4d}  {k}")

    print("\nrows with non-empty errorcode:")
    err_rows = [r for r in rows if r.get("errorcode")]
    print(len(err_rows))
    for r in err_rows:
        print(r["sessionId"], r["eventid"], r["errorcode"], r["errordescription"], r["datetime"])

    print("\ndistinct sessionIds:", sorted(set(r["sessionId"] for r in rows)))

    print("\nPLAYER_SESSION_EVENT sample eventdata (first 3):")
    n = 0
    for r in rows:
        if r["eventid"] == "PLAYER_SESSION_EVENT":
            print(r["eventdata"][:200])
            n += 1
            if n >= 3:
                break

    LOGGER.info("Completed analyze_debug_sample rows=%d input=%s", len(rows), args.input)


if __name__ == "__main__":
    main()
