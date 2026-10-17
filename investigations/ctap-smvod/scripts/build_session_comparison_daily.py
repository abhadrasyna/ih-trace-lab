#!/usr/bin/env python3
"""Builds one CSV row per (date, tenant) comparing the unique sessions in Lightstep, `unified_sessions` and the debug-events table.

Inputs per tenant/day (all local, no Athena/Lightstep calls; a missing input leaves its columns blank and is named in `missing_inputs`):
    Lightstep: `output/<T>/<date>_setupsession.csv`
    unified:   `data/athena/<T>/<date>_session.csv`
    debug:     `data/athena/<T>/<date>_debug_sessions.csv` (`run_athena_debug_sessions.py`)
A (date, tenant) with none of the three inputs is skipped. Re-running replaces the existing row for the same (date, tenant).
Output (default `output/session_comparison_daily.csv`): date, tenant, lightstep, unified, debug, L_and_U, L_and_D, U_and_D, L_and_U_and_D,
L_not_U, U_not_L, L_not_D, D_not_L, lightstep_blank_rows, missing_inputs. Sets are unique non-blank sessionIds; the day is UTC.

Usage:
    python3 build_session_comparison_daily.py --from 2026-10-14 --to 2026-10-14
    python3 build_session_comparison_daily.py --from 2026-10-08 --to 2026-10-16 --tenants SA,GH,ZM
"""
import argparse
import csv
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Mapping

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from compare_lightstep_athena_sessions import read_rows, unique_ids
from src.lib.logging.bootstrap import init_logging
from src.tenant_registry.registry import TenantRegistry

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.build_session_comparison_daily")
ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ["date", "tenant", "lightstep", "unified", "debug", "L_and_U", "L_and_D", "U_and_D", "L_and_U_and_D",
           "L_not_U", "U_not_L", "L_not_D", "D_not_L", "lightstep_blank_rows", "missing_inputs"]


def date_range(start: date, end: date) -> list[date]:
    """Pure: inclusive list of days; end before start raises."""
    if end < start:
        raise ValueError(f"--to {end} is before --from {start}")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _n(value: int | None) -> str:
    return "" if value is None else str(value)


def build_row(
    day: date, tenant: str, lightstep: set[str] | None, unified: set[str] | None, debug: set[str] | None, blank_rows: int | None
) -> dict[str, str]:
    """Pure: one output row; a count is blank when any set it needs is missing (None)."""
    def both(a: set[str] | None, b: set[str] | None) -> int | None:
        return None if a is None or b is None else len(a & b)

    def only(a: set[str] | None, b: set[str] | None) -> int | None:
        return None if a is None or b is None else len(a - b)

    all3 = None if lightstep is None or unified is None or debug is None else len(lightstep & unified & debug)
    missing = [name for name, s in (("lightstep", lightstep), ("unified", unified), ("debug", debug)) if s is None]
    return {
        "date": day.isoformat(), "tenant": tenant,
        "lightstep": _n(None if lightstep is None else len(lightstep)),
        "unified": _n(None if unified is None else len(unified)),
        "debug": _n(None if debug is None else len(debug)),
        "L_and_U": _n(both(lightstep, unified)), "L_and_D": _n(both(lightstep, debug)), "U_and_D": _n(both(unified, debug)),
        "L_and_U_and_D": _n(all3),
        "L_not_U": _n(only(lightstep, unified)), "U_not_L": _n(only(unified, lightstep)),
        "L_not_D": _n(only(lightstep, debug)), "D_not_L": _n(only(debug, lightstep)),
        "lightstep_blank_rows": _n(blank_rows), "missing_inputs": ";".join(missing),
    }


def upsert_rows(existing: list[Mapping[str, str]], new: list[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Pure: replaces existing rows sharing (date, tenant) with the new ones, sorted by (date, tenant)."""
    merged = {(r["date"], r["tenant"]): r for r in existing}
    merged.update({(r["date"], r["tenant"]): r for r in new})
    return [merged[k] for k in sorted(merged)]


def load_sets(root: Path, tenant: str, day: date) -> tuple[set[str] | None, set[str] | None, set[str] | None, int | None]:
    """Reads the three inputs; an absent file gives None for that set."""
    ls_path = root / "output" / tenant / f"{day}_setupsession.csv"
    uni_path = root / "data" / "athena" / tenant / f"{day}_session.csv"
    dbg_path = root / "data" / "athena" / tenant / f"{day}_debug_sessions.csv"
    lightstep, blank = (unique_ids(read_rows(ls_path, ["sessionId"])) if ls_path.exists() else (None, None))
    unified = unique_ids(read_rows(uni_path, ["sessionId"]))[0] if uni_path.exists() else None
    debug = unique_ids(read_rows(dbg_path, ["sessionId"]))[0] if dbg_path.exists() else None
    return lightstep, unified, debug, blank


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if list(reader.fieldnames or []) != COLUMNS:
            raise ValueError(f"{path}: unexpected columns {reader.fieldnames}; move it aside or fix it")
        return list(reader)


def main() -> None:
    init_logging("ctap-smvod-build_session_comparison_daily")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat, help="First UTC day, YYYY-MM-DD")
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat, help="Last UTC day, YYYY-MM-DD (inclusive)")
    ap.add_argument("--tenants", default=None, help="Comma-separated tenant codes (default: every code in config/tenants.yaml)")
    ap.add_argument("--root", type=Path, default=ROOT, help="Investigation root (default: ctap-smvod)")
    ap.add_argument("--out", type=Path, default=None, help="Output CSV (default: <root>/output/session_comparison_daily.csv)")
    args = ap.parse_args()

    tenants = [t.strip() for t in args.tenants.split(",") if t.strip()] if args.tenants else TenantRegistry().codes()
    out = args.out or args.root / "output" / "session_comparison_daily.csv"
    new_rows = []
    for day in date_range(args.start, args.end):
        for tenant in tenants:
            lightstep, unified, debug, blank = load_sets(args.root, tenant, day)
            if lightstep is None and unified is None and debug is None:
                LOGGER.info("%s %s: no inputs, skipped", tenant, day)
                continue
            new_rows.append(build_row(day, tenant, lightstep, unified, debug, blank))
    rows = upsert_rows(read_existing(out), new_rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("Wrote %s (%d rows, %d new/updated)", out, len(rows), len(new_rows))


if __name__ == "__main__":
    sys.exit(main())
