#!/usr/bin/env python3
"""
Extract every session whose error_codes contain a 1xxx code (exact 4-digit tokens, regex ^1\\d{3}$;
e.g. 1003 -- but not 6001, 3016 or E31012) from each tenant's
output/<TENANT>/YYYY-MM-DD_setupsession_with_outcome.csv, for several tenants at once. Same columns and
input/output conventions as extract_error_report_1xxx_6xxx.py (which it reuses); rows are NOT limited
to position_not_moved.

Reads existing pipeline outputs only -- never fires Athena/Lightstep. If any tenant/date input is
missing it aborts naming every missing file, so a partial result is never written.

Usage:
    # one date -> output/<TENANT>/YYYY-MM-DD_error_report_1xxx.csv per tenant
    python3 extract_error_report_1xxx.py --date 06102026

    # date range -> one .xlsx per tenant (one sheet per date): output/<TENANT>/<range>_error_report_1xxx.xlsx
    python3 extract_error_report_1xxx.py --from 01102026 --to 06102026 --tenants SA,GH
"""
import argparse
import logging
import os
import re
import sys
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

import extract_error_report_1xxx_6xxx as base
from lib.runtime import ddmmyyyy_to_date, investigation_output_dir, range_output_path, snapshot_output_path
from lib.webview import is_wv_cell

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.extract_error_report_1xxx")

DEFAULT_TENANTS = ("SA", "GH", "ZM")
ERROR_CODE_RE = re.compile(r"^1\d{3}$")
ARTIFACT = "error_report_1xxx"


def row_has_1xxx(row: dict) -> bool:
    """True if any ';'/','-separated token of the row's error_codes cell is an exact 1xxx code."""
    cell = row.get("error_codes", "") or ""
    tokens = (t.strip() for chunk in cell.split(";") for t in chunk.split(","))
    return any(ERROR_CODE_RE.match(t) for t in tokens)


def filter_rows(source_rows: list[dict], columns: list[str]) -> list[dict]:
    return [
        {c: r.get(c, "") for c in columns} | ({"is_wv": is_wv_cell(r)} if "is_wv" in columns else {})
        for r in source_rows if row_has_1xxx(r)
    ]


def parse_tenants(raw: str) -> list[str]:
    """Split a comma list into unique tenant codes; an empty list is an error."""
    tenants = list(dict.fromkeys(t.strip().upper() for t in raw.split(",") if t.strip()))
    if not tenants:
        raise ValueError("no tenants given")
    return tenants


def tenant_dir(tenant: str, output_root: str | None) -> Path:
    return Path(output_root) / tenant if output_root else investigation_output_dir(tenant=tenant)


def missing_inputs(tenants: list[str], dates: list[str], output_root: str | None) -> list[str]:
    """Every tenant/date input path that does not exist."""
    paths = (snapshot_output_path(d, "setupsession_with_outcome", output_dir=tenant_dir(t, output_root))
             for t in tenants for d in dates)
    return [p for p in paths if not os.path.exists(p)]


def main() -> None:
    init_logging("ctap-smvod-extract_error_report_1xxx")
    LOGGER.info("Starting extract_error_report_1xxx")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="Single date DDMMYYYY -> one CSV per tenant")
    ap.add_argument("--from", dest="date_from", help="Range start DDMMYYYY (with --to) -> one .xlsx per tenant, one sheet per date")
    ap.add_argument("--to", dest="date_to", help="Range end DDMMYYYY, inclusive")
    ap.add_argument("--tenants", default=",".join(DEFAULT_TENANTS), help="Comma-separated tenant codes (default: SA,GH,ZM)")
    ap.add_argument("--output-dir", default=None, help="Root holding <TENANT>/ output folders (default: investigation output dir)")
    ap.add_argument("--columns", default=",".join(base.DEFAULT_COLUMNS), help="Comma-separated columns to keep")
    args = ap.parse_args()

    if bool(args.date) == bool(args.date_from or args.date_to) or bool(args.date_from) != bool(args.date_to):
        ap.error("pass either --date, or both --from and --to")
    columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    try:
        tenants = parse_tenants(args.tenants)
        dates = [args.date] if args.date else base.dates_in_range(args.date_from, args.date_to)
        missing = missing_inputs(tenants, dates, args.output_dir)
        if missing:
            raise ValueError("setupsession_with_outcome.csv missing:\n  " + "\n  ".join(missing)
                             + "\nrun run_pipeline.py for those tenant/dates first (this script never fires Athena)")
        results = {t: {d: filter_rows(base.read_source(
            snapshot_output_path(d, "setupsession_with_outcome", output_dir=tenant_dir(t, args.output_dir))), columns)
            for d in dates} for t in tenants}
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    for tenant, per_date in results.items():
        out_dir = tenant_dir(tenant, args.output_dir)
        if args.date:
            out_path = snapshot_output_path(args.date, ARTIFACT, output_dir=out_dir)
            base.write_csv(out_path, columns, per_date[args.date])
        else:
            out_path = os.path.splitext(range_output_path(args.date_from, args.date_to, ARTIFACT, output_dir=out_dir))[0] + ".xlsx"
            base.write_xlsx(out_path, columns, {ddmmyyyy_to_date(d).isoformat(): rows for d, rows in per_date.items()})
        total = sum(len(r) for r in per_date.values())
        print(f"{tenant}: wrote {total} rows across {len(per_date)} date(s) to {out_path}", file=sys.stderr)
        LOGGER.info("Completed extract_error_report_1xxx tenant=%s rows=%d out=%s", tenant, total, out_path)


if __name__ == "__main__":
    main()
