#!/usr/bin/env python3
"""Extract the local error_eventdata rows for every session listed in an error-report CSV (e.g. the 3xxx household
report), joining householdId and deviceId back on. The sessionId lives inside the `eventdata` JSON (`sessionid`).
Reads data/athena/<TENANT>/*_error_eventdata.csv only -- never fires Athena. Sessions without any local rows are
logged (their date's file is likely not pulled).

Usage:
    python3 extract_household_error_eventdata.py \
        --report-csv ../output/ZA/2026-10-01_2026-10-19_error_report_3xxx_rD_saW-t.csv --tenant ZA
"""
import argparse
import csv
import glob
import json
import logging
import os
import sys

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.extract_household_error_eventdata")
SOURCE_COLUMNS = ["datetime", "messageid", "clientid", "eventclass", "eventid", "eventdata"]
OUT_COLUMNS = ["householdId", "deviceId", "sessionId", "source_file", *SOURCE_COLUMNS]
csv.field_size_limit(sys.maxsize)


def load_session_map(report_path: str) -> dict[str, dict]:
    """sessionId -> {householdId, deviceId} from the report CSV (blank sessionIds skipped)."""
    with open(report_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("householdId", "deviceId", "sessionId") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"column(s) {missing} missing in {report_path}")
        mapping = {r["sessionId"]: {"householdId": r["householdId"], "deviceId": r["deviceId"]}
                   for r in reader if (r["sessionId"] or "").strip()}
    if not mapping:
        raise ValueError(f"no sessions in {report_path}")
    return mapping


def session_id_of(row: dict) -> str:
    """sessionid from the eventdata JSON; '' when absent. Invalid JSON raises (fail loudly)."""
    data = json.loads(row["eventdata"]) if row.get("eventdata") else {}
    return str(data.get("sessionid") or "") if isinstance(data, dict) else ""


def filter_rows(rows: list[dict], session_map: dict[str, dict], source_file: str) -> list[dict]:
    """Rows whose eventdata sessionid is mapped, enriched with householdId/deviceId/sessionId/source_file."""
    out = []
    for r in rows:
        sid = session_id_of(r)
        if sid in session_map:
            out.append({c: r.get(c, "") for c in SOURCE_COLUMNS} | session_map[sid]
                       | {"sessionId": sid, "source_file": source_file})
    return out


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["sessionId"], r["datetime"]))


def read_csv_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in SOURCE_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"column(s) {missing} missing in {path}")
        return [{k: (v or "") for k, v in r.items()} for r in reader]


def main():
    init_logging("ctap-smvod-extract_household_error_eventdata")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report-csv", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--data-dir", default=None, help="Default: ../data/athena/<TENANT> relative to this script")
    ap.add_argument("--out", default=None, help="Default: <report-csv minus .csv>_error_eventdata.csv")
    args = ap.parse_args()

    data_dir = args.data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "athena", args.tenant)
    try:
        session_map = load_session_map(args.report_csv)
        files = sorted(glob.glob(os.path.join(data_dir, "*_error_eventdata.csv")))
        if not files:
            raise ValueError(f"no *_error_eventdata.csv in {data_dir}")
        rows = []
        for path in files:
            rows += filter_rows(read_csv_rows(path), session_map, os.path.basename(path))
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print("ERROR: no error_eventdata rows found locally for any session", file=sys.stderr)
        sys.exit(1)

    rows = sort_rows(rows)
    found = {r["sessionId"] for r in rows}
    absent = sorted(set(session_map) - found)
    out_path = args.out or os.path.splitext(args.report_csv)[0] + "_error_eventdata.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len(found)}/{len(session_map)} sessions) to {out_path}", file=sys.stderr)
    if absent:
        print(f"No local error_eventdata rows for {len(absent)} session(s): {', '.join(absent)}", file=sys.stderr)
    LOGGER.info("Completed extract_household_error_eventdata rows=%d sessions=%d/%d out=%s", len(rows), len(found),
                len(session_map), out_path)


if __name__ == "__main__":
    main()
