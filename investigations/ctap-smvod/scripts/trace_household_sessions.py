#!/usr/bin/env python3
"""
Trace one household's playback sessions end to end and write a table.

For a householdId it queries the Lightstep public API for the household's `sm-vod` sessions (EU project),
joins each session to its `go-mdrmfe` token (`brRef`, DRM type, `fcid`), follows the `fcid` into the US mDRM
project for the licence chain and the CDM device (make/model/security level), and, with `--athena`, adds the
client debug events (PLAYER_ERROR / PLAYING) from the month-suffixed debug-events table.
Lightstep keeps about 7 days; for older dates only `--athena` with `--device-id` gives results.

Usage:
    python3 trace_household_sessions.py --tenant ZA --hhid <householdId> --from 2026-11-03T12:00:00 --to 2026-11-03T15:00:00
    python3 trace_household_sessions.py --tenant ZA --hhid <id> --from 2026-10-19 --to 2026-10-30 --athena --table-suffix oct26

`--from`/`--to` are UTC (a date or `YYYY-MM-DDTHH:MM:SS`; a bare `--to` date is inclusive). Tokens come from
`LIGHTSTEP_API_KEY_EU` / `LIGHTSTEP_API_KEY_US` (environment or the gitignored root `.env`).
Output: CSV (default `output/<TENANT>/<hhid-prefix>_session_trace[_<suffix>].csv`) plus a printed summary.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.tenant_context import resolve_tenant_context

from scripts.lib import household_trace as ht
from scripts.lib.lightstep_api import LightstepError, Project, UrllibTransport, fetch_all_series, load_token
from scripts.lib.lightstep_export_kinds import resolve_target
from scripts.lib.lightstep_export_runner import ENDPOINTS
from src.lib.logging.bootstrap import init_logging
from src.tenant_registry import TenantRegistry

LOGGER = logging.getLogger(__name__)
LIGHTSTEP_RETENTION = timedelta(days=7)
OUTPUT_PERIOD_S = 60


def parse_utc(text: str, *, end: bool = False) -> datetime:
    """`YYYY-MM-DD` (end=True -> next midnight, i.e. inclusive day) or `YYYY-MM-DDTHH:MM:SS`, as UTC. ValueError if invalid."""
    try:
        if len(text) == 10:
            moment = datetime.strptime(text, "%Y-%m-%d") + (timedelta(days=1) if end else timedelta())
        else:
            moment = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"bad datetime {text!r}: use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS") from exc
    return moment.replace(tzinfo=timezone.utc)


def fmt_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def lightstep_part(tenant_code: str, hhid: str, oldest: datetime, youngest: datetime):
    """Runs the three Lightstep queries; returns (rows, device_ids). Raises LightstepError on API failure."""
    tenant = TenantRegistry().get(tenant_code)
    eu = resolve_target("smvod", tenant)
    us = resolve_target("mdrm-lrm", tenant)
    transport = UrllibTransport()

    def fetch(target, uql: str):
        base_url, org = ENDPOINTS[target.region.upper()]
        return fetch_all_series(transport, project=Project(base_url, org, target.project),
                                token=load_token(target.region), uql=uql, oldest=oldest, youngest=youngest,
                                output_period=OUTPUT_PERIOD_S)

    sm_vod = fetch(eu, ht.sm_vod_uql(hhid))
    mdrmfe = fetch(eu, ht.mdrmfe_uql(hhid))
    rows = ht.build_sessions(sm_vod, mdrmfe)
    fcids = [r.fcid for r in rows.values() if r.fcid]
    if fcids:
        ht.attach_chain(rows, fetch(us, ht.us_chain_uql(fcids)))
    return rows, ht.device_ids(sm_vod, mdrmfe)


def athena_part(args, hhid: str, device_ids: list[str], out_path: str) -> list[dict[str, str]]:
    """Live Athena query of every debug event for each `<deviceId>:<hhid>`; returns the CSV rows."""
    import run_athena_household_debug_events as dbg
    from lib.runtime import ensure_valid_credentials, run_athena_query

    ctx = resolve_tenant_context(args.tenant, table_suffix=args.table_suffix)
    client_ids = sorted(f"{d}:{hhid}" for d in device_ids)
    d_from, d_to = args.date_from, args.date_to
    query = dbg.build_query(ctx, ctx.database, client_ids, d_from, d_to)
    ensure_valid_credentials(ctx.profile)
    raw = out_path.removesuffix(".csv") + "_debug_events.csv"
    os.makedirs(os.path.dirname(os.path.abspath(raw)), exist_ok=True)
    run_athena_query(sql=query, params={}, output_path=raw, profile=ctx.profile, database=ctx.database,
                     workgroup="primary", output_location="s3://clarissaprod-apps-athena-query-results/",
                     region=ctx.region, poll_interval=2, timeout=900)
    with open(raw, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    init_logging("ctap-smvod-trace_household_sessions")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tenant", required=True, help="Tenant code from config/tenants.yaml (e.g. ZA)")
    ap.add_argument("--hhid", required=True, help="householdId")
    ap.add_argument("--from", dest="start", required=True, help="UTC start: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    ap.add_argument("--to", dest="end", required=True, help="UTC end (a bare date is inclusive)")
    ap.add_argument("--device-id", default=None, help="deviceId for --athena when Lightstep returns none (e.g. older than 7 days)")
    ap.add_argument("--athena", action="store_true", help="Also query the debug-events table (about 2 GB scanned per run)")
    ap.add_argument("--table-suffix", default=None, help="Month debug-events table suffix, e.g. oct26")
    ap.add_argument("--out", default=None, help="Output CSV path")
    args = ap.parse_args()

    try:
        hhid = ht.validate_hhid(args.hhid)
        oldest, youngest = parse_utc(args.start), parse_utc(args.end, end=True)
        if youngest <= oldest:
            raise ValueError("--to must be after --from")
        resolve_tenant_context(args.tenant, table_suffix=args.table_suffix)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    args.date_from, args.date_to = oldest.strftime("%Y-%m-%d"), (youngest - timedelta(seconds=1)).strftime("%Y-%m-%d")
    suffix = f"_{args.table_suffix}" if args.table_suffix else ""
    out_path = args.out or os.path.join(str(REPO_ROOT), "investigations", "ctap-smvod", "output", args.tenant,
                                        f"{hhid[:8]}_{hhid[-8:]}_session_trace{suffix}.csv")

    rows: dict[str, ht.SessionRow] = {}
    devices: list[str] = [args.device_id] if args.device_id else []
    if oldest < datetime.now(timezone.utc) - LIGHTSTEP_RETENTION:
        print("WARNING: window starts before the ~7 day Lightstep retention; older sessions will be missing.", file=sys.stderr)
    try:
        rows, found = lightstep_part(args.tenant, hhid, oldest, youngest)
        devices = sorted(set(devices) | set(found))
    except LightstepError as exc:
        print(f"ERROR: Lightstep failed: {exc}", file=sys.stderr)
        if not args.athena:
            sys.exit(1)

    athena_loaded = False
    if args.athena:
        if not devices:
            print("ERROR: --athena needs a deviceId: Lightstep found none, pass --device-id", file=sys.stderr)
            sys.exit(1)
        events = athena_part(args, hhid, devices, out_path)
        by_session = ht.summarize_athena(events)
        for sid, info in by_session.items():
            rows.setdefault(sid, ht.SessionRow(sid)).athena = info
        athena_loaded = True

    table = ht.to_table(rows, athena_loaded, fmt_ms)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ht.COLUMNS)
        writer.writeheader()
        writer.writerows(table)
    counts: dict[str, int] = {}
    for row in table:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    print(f"{len(table)} session(s) for {hhid} on {args.tenant}, devices={devices or 'none'} -> {out_path}")
    for outcome, n in sorted(counts.items()):
        print(f"  {outcome}: {n}")
    LOGGER.info("Completed trace_household_sessions sessions=%d out=%s", len(table), out_path)


if __name__ == "__main__":
    main()
