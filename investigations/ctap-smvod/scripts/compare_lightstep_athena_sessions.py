#!/usr/bin/env python3
"""Compares the unique sessionIds Lightstep and Athena saw for one tenant and UTC day.

Lightstep side: `output/<T>/<date>_setupsession.csv` (rows with a blank sessionId are counted and skipped).
Athena side: `data/athena/<T>/<date>_session.csv` (the `unified_sessions` partition for the day).
Optional enrichment from `data/athena/<T>/<date>_session_ingest.csv` (`run_athena_session_ingest.py`): the ingest time of
Athena-only sessions, and whether Lightstep-only sessions exist in Athena's D-1 partition or not at all.

Prints the counts and writes `output/<T>/<date>_lightstep_vs_athena_sessions.csv` (one row per session seen on one side only).

Usage:
    python3 compare_lightstep_athena_sessions.py --date 2026-10-14 --tenant ZA
"""
import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.compare_lightstep_athena_sessions")
ROOT = Path(__file__).resolve().parent.parent
OUT_COLUMNS = ["sessionId", "side", "lightstep_start_time", "athena_event_start", "athena_ingest_timestamp", "athena_elsewhere"]


def read_rows(path: Path, required: Sequence[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def unique_ids(rows: Iterable[Mapping[str, str]]) -> tuple[set[str], int]:
    """Pure: non-blank sessionIds and the number of rows skipped for a blank one."""
    ids, blank = set(), 0
    for r in rows:
        sid = (r.get("sessionId") or "").strip()
        if sid:
            ids.add(sid)
        else:
            blank += 1
    return ids, blank


def diff_sets(lightstep: set[str], athena: set[str]) -> dict[str, set[str]]:
    """Pure: sessions on both sides, only in Lightstep, only in Athena."""
    return {"both": lightstep & athena, "lightstep_only": lightstep - athena, "athena_only": athena - lightstep}


def venn3(lightstep: set[str], unified: set[str], debug: set[str]) -> dict[str, int]:
    """Pure: sizes of the seven regions of three session sets (L=Lightstep, U=unified_sessions, D=debug events)."""
    return {
        "L only": len(lightstep - unified - debug),
        "U only": len(unified - lightstep - debug),
        "D only": len(debug - lightstep - unified),
        "L&U only": len((lightstep & unified) - debug),
        "L&D only": len((lightstep & debug) - unified),
        "U&D only": len((unified & debug) - lightstep),
        "L&U&D": len(lightstep & unified & debug),
    }


def mismatch_rows(
    parts: Mapping[str, set[str]],
    ls_start: Mapping[str, str],
    ingest: Mapping[str, Mapping[str, str]],
    ingest_loaded: bool,
) -> list[dict[str, str]]:
    """Pure: one output row per one-sided session, enriched from the Lightstep start_time and the Athena ingest export."""
    out = []
    for side in ("lightstep_only", "athena_only"):
        for sid in sorted(parts[side]):
            i = ingest.get(sid, {})
            elsewhere = ""
            if side == "lightstep_only" and ingest_loaded:
                elsewhere = "athena_d_minus_1" if i else "not_in_athena_d_or_d_minus_1"
            out.append({
                "sessionId": sid, "side": side, "lightstep_start_time": ls_start.get(sid, ""),
                "athena_event_start": i.get("event_start", ""), "athena_ingest_timestamp": i.get("ingest_timestamp", ""),
                "athena_elsewhere": elsewhere,
            })
    return out


def earliest_start(rows: Iterable[Mapping[str, str]]) -> dict[str, str]:
    """Pure: earliest non-blank start_time string per sessionId (ISO-like strings sort chronologically)."""
    first: dict[str, str] = {}
    for r in rows:
        sid, ts = (r.get("sessionId") or "").strip(), (r.get("start_time") or "").strip()
        if sid and ts and (sid not in first or ts < first[sid]):
            first[sid] = ts
    return first


def index_ingest(rows: Iterable[Mapping[str, str]]) -> dict[str, Mapping[str, str]]:
    """Pure: ingest rows keyed by sessionId; a duplicate id raises (the export is one row per session)."""
    out: dict[str, Mapping[str, str]] = {}
    for r in rows:
        sid = r["sessionId"]
        if sid in out:
            raise ValueError(f"duplicate sessionId in ingest export: {sid}")
        out[sid] = r
    return out


def main() -> None:
    init_logging("ctap-smvod-compare_lightstep_athena_sessions")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="UTC day, YYYY-MM-DD")
    ap.add_argument("--tenant", default="ZA")
    ap.add_argument("--root", type=Path, default=ROOT, help="Investigation root (default: ctap-smvod)")
    ap.add_argument("--debug", action="store_true",
                    help="3-way: add the debug-events sessions from <date>_debug_sessions.csv (run_athena_debug_sessions.py)")
    args = ap.parse_args()

    ls_rows = read_rows(args.root / "output" / args.tenant / f"{args.date}_setupsession.csv", ["sessionId", "start_time"])
    ath_rows = read_rows(args.root / "data" / "athena" / args.tenant / f"{args.date}_session.csv", ["sessionId"])
    ingest_path = args.root / "data" / "athena" / args.tenant / f"{args.date}_session_ingest.csv"
    ingest_loaded = ingest_path.exists()
    ingest = index_ingest(read_rows(ingest_path, ["sessionId", "event_start", "ingest_timestamp"])) if ingest_loaded else {}

    ls_ids, ls_blank = unique_ids(ls_rows)
    ath_ids, _ = unique_ids(ath_rows)
    parts = diff_sets(ls_ids, ath_ids)
    out_rows = mismatch_rows(parts, earliest_start(ls_rows), ingest, ingest_loaded)
    dbg_ids: set[str] | None = None
    if args.debug:
        dbg_rows = read_rows(args.root / "data" / "athena" / args.tenant / f"{args.date}_debug_sessions.csv", ["sessionId"])
        dbg_ids, _ = unique_ids(dbg_rows)
        for r in out_rows:
            r["in_debug"] = "yes" if r["sessionId"] in dbg_ids else "no"
    columns = OUT_COLUMNS + (["in_debug"] if args.debug else [])

    out = args.root / "output" / args.tenant / f"{args.date}_lightstep_vs_athena_sessions.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(out_rows)

    print(f"{args.tenant} {args.date}: Lightstep {len(ls_ids)} sessions ({ls_blank} rows with blank sessionId skipped), Athena {len(ath_ids)}")
    for key in ("both", "lightstep_only", "athena_only"):
        print(f"  {key}: {len(parts[key])}")
    if ingest_loaded:
        elsewhere = [r["athena_elsewhere"] for r in out_rows if r["side"] == "lightstep_only"]
        for label in sorted(set(elsewhere)):
            print(f"  lightstep_only -> {label}: {elsewhere.count(label)}")
    if dbg_ids is not None:
        print(f"  debug events: {len(dbg_ids)} sessions")
        for label, n in venn3(ls_ids, ath_ids, dbg_ids).items():
            print(f"  {label}: {n}")
    LOGGER.info("Wrote %s (%d rows)", out, len(out_rows))


if __name__ == "__main__":
    sys.exit(main())
