"""Export one tenant's daily Lightstep CSVs (ctap, smvod, smvod-ts, mdrmfe and the four mDRM kinds) through the public API.

Writes ``<date>_<kind>.csv`` in the UI export format into ``data/lightstep/<TENANT>/`` (or ``--output-dir``),
then runs the Step 0 input check on that folder. Existing files are skipped unless ``--force`` is given.
Lightstep keeps about 7 days, so run within a week of the UTC day. Tokens come from ``LIGHTSTEP_API_KEY_EU`` /
``LIGHTSTEP_API_KEY_US`` in the environment or the gitignored root ``.env``.

Usage:
    python3 export_lightstep_day.py --tenant ZA
    python3 export_lightstep_day.py --tenant ZM --date 2026-10-29 --kinds ctap smvod --output-dir /tmp/ls --force
Exit code: 0 only when every kind was written (or skipped) and the input check passed.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.lightstep_inputs import Settings, format_legend, format_report, has_failures, validate_tenant
from lib.tenant_context import lightstep_dir, resolve_tenant_context

from scripts.lib.lightstep_api import Transport, UrllibTransport
from scripts.lib.lightstep_export_kinds import KINDS, resolve_target
from scripts.lib.lightstep_export_runner import (
    Dependencies,
    EnvTokenProvider,
    ExportRequest,
    InputCheck,
    print_report,
    run_export,
)
from src.lib.logging.bootstrap import init_logging
from src.tenant_registry import TenantRegistry


def default_date(now: datetime | None = None) -> str:
    """Yesterday in UTC as ``YYYY-MM-DD``."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return (moment.date() - timedelta(days=1)).isoformat()


def make_input_check(tenant_code: str, day: str) -> InputCheck:
    """Returns a check that validates a folder with the Step 0 validator for ``tenant_code`` and ``day``."""

    def check(directory: Path, include_drm: bool) -> tuple[str, bool]:
        findings = validate_tenant(directory, day, resolve_tenant_context(tenant_code), Settings(include_drm=include_drm))
        return "\n".join([format_report(tenant_code, findings), format_legend()]), not has_failures(findings)

    return check


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tenant", required=True, help="Tenant code from config/tenants.yaml, e.g. ZA")
    ap.add_argument("--date", default=None, help="UTC day as YYYY-MM-DD (default: yesterday UTC)")
    ap.add_argument("--kinds", nargs="+", default=list(KINDS), choices=list(KINDS), help="Kinds to export (default: all eight)")
    ap.add_argument("--output-dir", type=Path, default=None, help="Folder for the CSVs and the input check (default: data/lightstep/<TENANT>)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files instead of skipping them")
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None, transport: Transport | None = None, input_check: InputCheck | None = None) -> int:
    """Composition root: the only place that picks the real transport, tokens and input check."""
    init_logging("export-lightstep-day")
    args = parse_args(argv)
    day = args.date or default_date()
    try:
        Date.fromisoformat(day)
        tenant = TenantRegistry().get(args.tenant)
    except (ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    deps = Dependencies(
        transport=transport or UrllibTransport(), tokens=EnvTokenProvider(), resolve_target=resolve_target,
        input_check=input_check or make_input_check(tenant.code, day), report=print_report,
    )
    request = ExportRequest(tenant=tenant, day=day, kinds=args.kinds, out_dir=args.output_dir or lightstep_dir(tenant.code), force=args.force)
    return run_export(request, deps)


if __name__ == "__main__":
    sys.exit(main())
