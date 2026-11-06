"""Live smoke test: run one short UTC slice of an export kind through the Lightstep API and print a summary."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Imports sit below the sys.path bootstrap so the script runs as `python scripts/...` (E402 is intended).
from scripts.lib.lightstep_api import Project, UrllibTransport, fetch_all_series, load_token  # noqa: E402
from scripts.lib.lightstep_export_kinds import expand_query, get_kind, resolve_target  # noqa: E402
from src.lib.logging.bootstrap import init_logging  # noqa: E402
from src.tenant_registry import TenantRegistry  # noqa: E402

ENDPOINTS = {
    "eu": ("https://api.eu.lightstep.com/public/v0.2", "Synamedia-EU"),
    "us": ("https://api.lightstep.com/public/v0.2", "Synamedia"),
}


def slice_window(start: str, minutes: int) -> tuple[datetime, datetime]:
    """Return the UTC ``(oldest, youngest)`` bounds of a slice starting at ``start``."""

    if minutes <= 0:
        raise ValueError(f"--minutes must be positive, got {minutes}")
    start_dt = datetime.fromisoformat(start)
    oldest = start_dt.replace(tzinfo=timezone.utc) if start_dt.tzinfo is None else start_dt.astimezone(timezone.utc)
    return oldest, oldest + timedelta(minutes=minutes)


def main(argv: list[str] | None = None) -> int:
    """Fetch one slice for ``--kind``/``--tenant`` and print series count, window and a sample series."""

    init_logging("probe-lightstep-slice")
    logger = logging.getLogger("scripts.probe_lightstep_slice")
    logger.info("Run started")
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--kind", required=True)
        parser.add_argument("--tenant", required=True)
        parser.add_argument("--start", required=True, help="UTC slice start, e.g. 2026-10-31T10:00:00")
        parser.add_argument("--minutes", type=int, default=10)
        args = parser.parse_args(argv)

        tenant = TenantRegistry().get(args.tenant)
        target = resolve_target(args.kind, tenant)
        base_url, org = ENDPOINTS[target.region.lower()]
        oldest, youngest = slice_window(args.start, args.minutes)
        series = fetch_all_series(
            UrllibTransport(),
            project=Project(base_url, org, target.project),
            token=load_token(target.region.lower()),
            uql=expand_query(args.kind, tenant),
            oldest=oldest,
            youngest=youngest,
        )
        print(f"kind={args.kind} tenant={args.tenant} project={target.project} region={target.region}")
        print(f"window={oldest.isoformat()}..{youngest.isoformat()} series={len(series)}")
        print(f"expected_columns={get_kind(args.kind).columns if hasattr(get_kind(args.kind), 'columns') else 'n/a'}")
        if series:
            print(f"sample={str(series[0])[:400]}")
        return 0
    finally:
        logger.info("Run finished")


if __name__ == "__main__":
    raise SystemExit(main())
