"""Daily household usage report CLI: load the roster, fetch Athena and Lightstep data per tenant, merge, render and write `reports/usage/<TENANT>/<date>.md`.

Each source reads the local ctap-smvod export by default and queries live only with its flag. A failure for a tenant writes `<date>.FAILED.txt` ("report not generated") next to where the report
would be and makes the exit code non-zero; a partial report is never written.
"""
from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from src.lib.logging.bootstrap import init_logging
from src.tenant_registry.registry import TenantRegistry

from .. import roster
from ..athena_source import LocalExportSource as LocalAthenaSource
from ..athena_source import SessionRow, SessionSource
from ..errors import UsageTrackingError
from ..lightstep_source import LocalExportSource as LocalLightstepSource
from ..lightstep_source import RequestSource
from ..merge import HouseholdDay, build_household_day, trend_days
from ..render import render_report
from ..roster import Household
from ..rules import apply_rules

LOGGER = logging.getLogger(__name__)

FCID_SLUG = "daily-usage-report"
DEFAULT_OFFSET_DAYS = 2
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[4] / "reports" / "usage"


@dataclass(frozen=True)
class Wiring:
    """Builds the per-tenant sources; the only place concrete clients appear, so tests inject fakes here."""

    session_source: Callable[[str, bool, date], SessionSource]
    request_source: Callable[[str, bool], RequestSource]


def default_wiring(registry: TenantRegistry | None = None) -> Wiring:
    def tenant_config(tenant: str):
        return (registry or TenantRegistry()).get(tenant)

    def session_source(tenant: str, live: bool, today: date) -> SessionSource:
        if not live:
            return LocalAthenaSource(tenant)
        from ..live_clients import make_athena_source

        return make_athena_source(tenant_config(tenant), today)

    def request_source(tenant: str, live: bool) -> RequestSource:
        if not live:
            return LocalLightstepSource(tenant)
        from ..live_clients import make_lightstep_source

        return make_lightstep_source(tenant_config(tenant))

    return Wiring(session_source, request_source)


def build_tenant_days(
    households: list[Household], day: date, sessions: SessionSource, requests: RequestSource,
) -> list[HouseholdDay]:
    """Fetch the trailing window and merge it per household. Households must all belong to the source's tenant."""
    by_day = {d: sessions.fetch_sessions(households, d) for d in trend_days(day)}
    window: list[SessionRow] = [s for rows in by_day.values() for s in rows]
    errors = sessions.fetch_errors(by_day[day], day)
    request_rows = requests.fetch_requests(households, day)
    return [
        apply_rules(build_household_day(h, day, window, sessions.fetch_household_devices(h, day), errors, request_rows))
        for h in households
    ]


def run_tenant(tenant: str, households: list[Household], day: date, args: argparse.Namespace, wiring: Wiring, today: date) -> Path:
    sessions = wiring.session_source(tenant, args.live_athena, today)
    requests = wiring.request_source(tenant, args.live_lightstep)
    days = build_tenant_days(households, day, sessions, requests)
    return _write(args.out_dir / tenant / f"{day}.md", render_report(tenant, day, days))


def main(argv: list[str] | None = None, wiring: Wiring | None = None, today: date | None = None) -> int:
    init_logging(FCID_SLUG)
    args = _parse(argv, today or date.today())
    day = date.fromisoformat(args.date)
    config = roster.resolve_config_path(args.config)
    LOGGER.info("run start", extra={"date": str(day), "config": str(config)})
    started = time.monotonic()
    try:
        grouped = roster.by_tenant(roster.load(config))
    except UsageTrackingError as exc:
        LOGGER.error("roster load failed: %s", exc)
        _write(args.out_dir / f"{day}.FAILED.txt", f"report not generated for {day}: {exc}\n")
        return 1
    failed = 0
    (args.out_dir / f"{day}.FAILED.txt").unlink(missing_ok=True)
    wiring = wiring or default_wiring()
    for tenant, households in grouped.items():
        failed += _run_one(tenant, households, day, args, wiring, today or date.today())
    LOGGER.info("run end", extra={"tenants": len(grouped), "failed": failed, "duration_ms": int((time.monotonic() - started) * 1000)})
    return 1 if failed else 0


def _run_one(tenant: str, households: list[Household], day: date, args: argparse.Namespace, wiring: Wiring, today: date) -> int:
    report = args.out_dir / tenant / f"{day}.md"
    failed_note = args.out_dir / tenant / f"{day}.FAILED.txt"
    try:
        path = run_tenant(tenant, households, day, args, wiring, today)
    except Exception as exc:  # one tenant's failure, expected or not, must not stop the others or leave no note
        LOGGER.error("tenant %s failed: %s", tenant, exc, exc_info=not isinstance(exc, UsageTrackingError))
        report.unlink(missing_ok=True)
        _write(failed_note, f"report not generated for {tenant} {day}: {exc}\n")
        return 1
    failed_note.unlink(missing_ok=True)
    LOGGER.info("report written", extra={"tenant": tenant, "path": str(path), "households": len(households)})
    return 0


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def _parse(argv: list[str] | None, today: date) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=str(today - timedelta(days=DEFAULT_OFFSET_DAYS)), help="Report day YYYY-MM-DD (default: two days ago, the newest day the download pipeline has exported).")
    parser.add_argument("--config", default=None, help="Roster YAML (default: TRACK_CONFIG or config/tracked_households.yaml).")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Reports root; one folder per tenant.")
    parser.add_argument("--live-athena", action="store_true", help="Query Athena live instead of reading the local export.")
    parser.add_argument("--live-lightstep", action="store_true", help="Query Lightstep live instead of reading the local export.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
