"""Fetch the Shaka 6001 guest-login redirect rows and the redirected guests' debug events, one file pair per UTC day.

For every date in ``--start-date``..``--end-date`` without a saved file it runs two registered queries through an injected
Athena client: ``fact-navigation-interactions-guest-login-redirect`` -> ``<date>_guest_login_redirect.csv`` and
``guest-redirect-debug-events`` -> ``<date>_guest_redirect_debug_events.csv`` (debug ``clientid`` is
``<device_id>:<user_id>``). Dates already saved are skipped, so reruns and cron are idempotent; to refetch a date delete
its files. Dates are fetched serially (no concurrency, so no FCID propagation). Base: events; tenant: see ``--tenant``.
``GUEST.*`` ids are per-install, not real households or devices.

Scan: about 650 MB of the debug table per missing date (the navigation table is small). ``--dry-run`` prints the missing
dates and that estimate without credentials or queries. Without ``--dry-run`` AWS credentials are checked first and the
run fails fast (no SSO prompt) when they are missing or expired.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT, REPO_ROOT / "vendor" / "athena-mcp-server" / "src"):
    if _path.exists() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.athena_fetch import FetchError, FetchResult, fetch_missing  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, daily_filename  # noqa: E402
from src.lib.athena.protocols import AthenaClient  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.fetch_guest_login_redirects")
REDIRECT_QUERY = "fact-navigation-interactions-guest-login-redirect"
DEBUG_QUERY = "guest-redirect-debug-events"
REDIRECT_ARTIFACT = "guest_login_redirect"
DEBUG_ARTIFACT = "guest_redirect_debug_events"
REDIRECT_FIELDS = [
    "user_id", "device_id", "device_type", "uid", "nav_event_time", "timestamp_formatted", "navigation_start_time",
    "navigation_end_time", "nav_step_num", "nav_step_total", "nav_start_event", "nav_end_event", "start_reason",
    "end_reason", "event_type", "event", "event_code", "event_source", "event_source_ex", "event_source_ex_name",
    "source_name", "event_details",
]
DEBUG_FIELDS = ["datetime", "clientid", "eventclass", "eventid", "eventdata"]
DEBUG_MB_PER_DAY = 650


class RedirectFetchError(Exception):
    """Raised when credentials, tenant or client wiring is unusable."""


def missing_dates(dates: list[date], out_dir: Path) -> list[date]:
    """Dates for which either output file is absent or empty."""
    def present(day: date, artifact: str) -> bool:
        path = out_dir / daily_filename(day, artifact)
        return path.is_file() and path.stat().st_size > 0
    return [d for d in dates if not (present(d, REDIRECT_ARTIFACT) and present(d, DEBUG_ARTIFACT))]


def estimate_scan_mb(missing: list[date]) -> int:
    return len(missing) * DEBUG_MB_PER_DAY


def fetch_redirects(client: AthenaClient, dates: list[date], out_dir: Path, *, database: str,
                    debug_events_table: str) -> tuple[FetchResult, FetchResult]:
    """Fetch both artifacts for the dates not yet saved; a date saved by only one query refetches just the other."""
    redirects = fetch_missing(client, REDIRECT_QUERY, dates, artifact=REDIRECT_ARTIFACT, out_dir=out_dir,
                              params={"database": database}, fieldnames=REDIRECT_FIELDS)
    debug = fetch_missing(client, DEBUG_QUERY, dates, artifact=DEBUG_ARTIFACT, out_dir=out_dir,
                          params={"database": database, "debug_events_table": debug_events_table},
                          fieldnames=DEBUG_FIELDS)
    return redirects, debug


def check_credentials(profile: str) -> None:
    """Fail fast, without an SSO prompt, when the AWS profile has no valid credentials."""
    try:
        import boto3

        boto3.Session(profile_name=profile).client("sts").get_caller_identity()
    except Exception as exc:  # boundary: boto3/botocore types must not leak
        raise RedirectFetchError(
            f"AWS credentials for profile {profile} are missing or expired ({exc}); run: aws sso login --profile {profile}"
        ) from exc


def build_client(profile: str, region: str, database: str, output_dir: Path) -> AthenaClient:
    try:
        from athena_runner.aws_clients import AwsClientFactory
        from athena_runner.config import RunConfig
        from athena_runner.query_executor import BotoAthenaQueryExecutor
        from athena_runner.result_downloader import S3ResultDownloader

        from src.lib.athena.adapter import AthenaAdapter

        factory = AwsClientFactory(profile, region=region)
        run_config = RunConfig(
            profile=profile, workgroup="primary", output_location="s3://clarissaprod-apps-athena-query-results/",
            output_dir=str(output_dir), region=region, poll_interval_seconds=2, timeout_seconds=300,
        )
        return AthenaAdapter(BotoAthenaQueryExecutor(factory.athena_client(), run_config),
                             S3ResultDownloader(factory.s3_client()), run_config, database=database)
    except Exception as exc:  # boundary: wiring failures surface as one of our own errors
        raise RedirectFetchError(f"cannot build the Athena client: {exc}") from exc


def resolve_tenant(code: str) -> dict[str, str]:
    from src.tenant_registry import AthenaQueryTarget, TenantRegistry

    try:
        tenant = TenantRegistry().get(code)
    except KeyError as exc:
        raise RedirectFetchError(f"unknown tenant {code}") from exc
    context = AthenaQueryTarget().build_context(tenant)
    return {**{k: str(v) for k, v in context.items()}, "debug_events_table": f"{tenant.athena_tenant_id}_ccl_debug_events"}


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--dry-run", action="store_true", help="list missing dates and the scan estimate; no credentials, no queries")
    return parser


def main(argv: list[str] | None = None, *, client_factory: Callable[..., AthenaClient] = build_client,
         credential_check: Callable[[str], None] = check_credentials) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-fetch-guest-login-redirects")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    try:
        resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
        out_dir = resolver.resolve_investigation_data_dir(SLUG, "athena", tenant=args.tenant)
        dates = date_range(args.start_date, args.end_date)
        missing = missing_dates(dates, out_dir)
        print(f"tenant={args.tenant} base=events missing_dates={','.join(d.isoformat() for d in missing) or 'none'} "
              f"estimated_scan_mb={estimate_scan_mb(missing)} out_dir={out_dir}")
        if args.dry_run or not missing:
            return 0
        tenant = resolve_tenant(args.tenant)
        credential_check(tenant["profile"])
        client = client_factory(tenant["profile"], tenant["region"], tenant["database"], out_dir)
        redirects, debug = fetch_redirects(client, missing, out_dir, database=tenant["database"],
                                           debug_events_table=tenant["debug_events_table"])
    except (RedirectFetchError, FetchError, LocalDataError) as exc:
        LOGGER.error("Guest-login redirect fetch failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"saved redirect_files={len(redirects.saved)} debug_files={len(debug.saved)} "
          f"skipped={len(redirects.skipped)} (GUEST.* ids are per-install, not real households/devices)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
