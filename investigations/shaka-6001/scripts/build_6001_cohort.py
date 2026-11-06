"""Build the Shaka 6001 cohort and make sure its playback-outcome session data is available locally.

Cohort: every device/household (``clientid`` = ``<deviceId>:<householdId>``) with at least one 6001 in the enriched
events (``build_enriched_events`` output for the same range), carrying the period, webview flag and device model of
its first 6001 (earliest timestamp; UTC converted to IST for the first-6001 day). ``GUEST.*`` ids are per-install, so
they are flagged ``is_guest`` and kept apart from real households in the counts.

Session data: per-date ``playback_outcome`` rows (``ctap-smvod-playback-outcome``, one row per session) are read from
the local sources first; only dates found nowhere are fetched through the injected Athena client, serially (one blocking
query at a time, so there is no concurrent FCID to propagate), and saved locally. Cohort members with no session rows
are counted in the coverage line, not treated as failures. Base: households/devices (cohort), sessions (outcome data);
tenant: see ``--tenant``. Rerunning overwrites the cohort file and never refetches a date already saved locally.
``--dry-run`` lists the dates that would be fetched and touches neither AWS nor the output file.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

INVESTIGATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INVESTIGATION_ROOT.parents[1]
for _path in (REPO_ROOT, INVESTIGATION_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.lib.analysis_config import DEFAULT_CONFIG_PATH, AnalysisConfig, load_config  # noqa: E402
from scripts.lib.athena_fetch import FetchError, fetch_missing  # noqa: E402
from scripts.lib.local_data import SLUG, LocalDataError, date_range, default_sources, load_daily  # noqa: E402
from src.lib.athena.protocols import AthenaClient  # noqa: E402
from src.lib.csv_io.csv_file import CsvFileReader, CsvFileWriter  # noqa: E402
from src.lib.paths import YamlPathResolver  # noqa: E402

LOGGER = logging.getLogger("investigations.shaka_6001.scripts.build_6001_cohort")
ENRICHED_ARTIFACT = "shaka6001_enriched"
OUTPUT_ARTIFACT = "6001_cohort"
SESSION_ARTIFACT = "session"
QUERY_NAME = "ctap-smvod-playback-outcome"
SESSION_FIELDNAMES = [
    "sessionId", "householdId", "deviceId", "content", "playback_outcome", "event_start", "event_end",
    "startup_time_ms", "buffering_count", "buffering_total_ms",
]
FIELDNAMES = [
    "clientid", "device_id", "household_id", "is_guest", "first_6001_utc", "first_6001_ist", "first_6001_date_ist",
    "period", "period_conflict", "is_webview", "device_model", "events_6001", "session_rows", "has_session_rows",
]
IST = ZoneInfo("Asia/Kolkata")
GUEST_PREFIX = "GUEST."
CODE_6001 = "6001"


class CohortError(Exception):
    """Raised for unusable inputs (enriched events, credentials, client wiring)."""


@dataclass(frozen=True)
class Coverage:
    members: int
    guests: int
    with_sessions: int
    without_sessions: int
    session_rows: int
    skipped_rows: int  # enriched rows without a usable device/household id, not in the cohort
    bad_timestamp_rows: int = 0  # 6001 rows with an unreadable timestamp (kept in counts, ignored for "first")
    members_without_timestamp: int = 0  # members whose every timestamp is unreadable; period taken from their first row

    def line(self, tenant: str) -> str:
        return (
            f"tenant={tenant} base=households/devices members={self.members} (guests={self.guests}) "
            f"with_session_rows={self.with_sessions} without_session_rows={self.without_sessions} "
            f"(counted, not failures) session_rows={self.session_rows} enriched_rows_without_id={self.skipped_rows} "
            f"bad_timestamp_rows={self.bad_timestamp_rows} members_without_timestamp={self.members_without_timestamp}"
        )


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def client_key(device_id: str, household_id: str) -> str:
    return f"{device_id}:{household_id}"


def _is_6001(row: dict[str, str]) -> bool:
    # The source file is the 6001 extract; only a row that names a different code is excluded.
    return (row.get("shaka_code") or CODE_6001).strip() == CODE_6001


@dataclass(frozen=True)
class CohortBuild:
    members: list[dict]
    skipped_rows: int
    bad_timestamp_rows: int
    members_without_timestamp: int


def build_cohort(enriched_rows: Iterable[dict[str, str]]) -> CohortBuild:
    """One row per (device, household) from its earliest 6001; unreadable timestamps and missing ids are counted."""
    members: dict[tuple[str, str], dict] = {}
    skipped = bad_ts = 0
    for row in enriched_rows:
        if not _is_6001(row):
            continue
        ident = ((row.get("device_id") or "").strip(), (row.get("household_id") or "").strip())
        if not ident[0] or not ident[1] or ":" in ident[0]:  # clientid splits on the first ':', so a device id has none
            skipped += 1
            continue
        ts = _parse_utc(row.get("datetime"))
        bad_ts += ts is None
        member = members.setdefault(ident, {"row": row, "ts": ts, "count": 0})
        member["count"] += 1
        if ts is not None and (member["ts"] is None or ts < member["ts"]):
            member["row"], member["ts"] = row, ts
    cohort = [_member_row(ident, m["row"], m["ts"], m["count"]) for ident, m in members.items()]
    cohort.sort(key=lambda r: (r["first_6001_utc"] or "~", r["clientid"]))
    return CohortBuild(cohort, skipped, bad_ts, sum(not r["first_6001_utc"] for r in cohort))


def _member_row(ident: tuple[str, str], first: dict[str, str], ts: datetime | None, count: int) -> dict:
    device, household = ident
    ist = ts.astimezone(IST) if ts else None
    return {
        "clientid": client_key(device, household), "device_id": device, "household_id": household,
        "is_guest": household.startswith(GUEST_PREFIX) or device.startswith(GUEST_PREFIX),
        "first_6001_utc": ts.isoformat() if ts else "",
        "first_6001_ist": ist.isoformat() if ist else "",
        "first_6001_date_ist": ist.date().isoformat() if ist else "",
        "period": first.get("period", "") or "unknown",
        "period_conflict": first.get("period_conflict", ""),
        "is_webview": first.get("is_webview", ""),
        "device_model": first.get("device_model", ""),
        "events_6001": count, "session_rows": 0, "has_session_rows": False,
    }


def attach_session_counts(cohort: list[dict], session_rows: Iterable[dict[str, str]]) -> Coverage:
    """Fill ``session_rows``/``has_session_rows`` per member (matched on device+household); returns coverage."""
    counts: Counter[tuple[str, str]] = Counter()
    total = 0
    for row in session_rows:
        if "deviceId" not in row or "householdId" not in row:
            raise CohortError("session rows lack deviceId/householdId; a local 'session' file is not playback-outcome data")
        total += 1
        counts[((row.get("deviceId") or "").strip(), (row.get("householdId") or "").strip())] += 1
    for member in cohort:
        member["session_rows"] = counts.get((member["device_id"], member["household_id"]), 0)
        member["has_session_rows"] = member["session_rows"] > 0
    with_sessions = sum(m["has_session_rows"] for m in cohort)
    return Coverage(
        members=len(cohort), guests=sum(m["is_guest"] for m in cohort), with_sessions=with_sessions,
        without_sessions=len(cohort) - with_sessions, session_rows=total, skipped_rows=0,
    )


def check_credentials(profile: str, region: str) -> None:
    """Fail fast, with no SSO prompt, when the profile has no valid credentials (cron has no TTY)."""
    try:
        import boto3

        boto3.Session(profile_name=profile, region_name=region).client("sts").get_caller_identity()
    except Exception as exc:  # boundary: botocore errors never leak
        raise CohortError(
            f"AWS credentials for profile '{profile}' are missing or expired; run 'aws sso login --profile {profile}'"
        ) from exc


def make_client(tenant: str) -> AthenaClient:
    """Real Athena client for ``tenant`` after the credential pre-check; imported lazily so tests never need AWS."""
    from src.pipelines.aws_access_cli.runtime import RuntimeConfig, make_athena_client
    from src.tenant_registry import AthenaQueryTarget, TenantRegistry

    try:
        context = AthenaQueryTarget().build_context(TenantRegistry().get(tenant))
        vendor = REPO_ROOT / "vendor" / "athena-mcp-server" / "src"
        if vendor.exists() and str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
        runtime = RuntimeConfig(profile=str(context["profile"]), region=str(context["region"]))
        check_credentials(runtime.profile, runtime.region)
        return make_athena_client(runtime, str(context["database"]))
    except CohortError:
        raise
    except Exception as exc:  # boundary: registry/boto3/athena_runner errors never leak
        raise CohortError(f"cannot build the Athena client for tenant {tenant}: {exc}") from exc


def tenant_database(tenant: str) -> str:
    from src.tenant_registry import AthenaQueryTarget, TenantRegistry

    try:
        return str(AthenaQueryTarget().build_context(TenantRegistry().get(tenant))["database"])
    except Exception as exc:  # boundary
        raise CohortError(f"cannot resolve the Athena database for tenant {tenant}: {exc}") from exc


def read_enriched(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise CohortError(f"enriched events not found: {path}; run build_enriched_events for the same range first")
    try:
        return list(CsvFileReader().read_rows(str(path)))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CohortError(f"cannot read {path}: {exc}") from exc


def write_cohort(path: Path, rows: list[dict]) -> None:
    """Write via a sibling temp file so a failed run never leaves a half-written output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    CsvFileWriter().write_rows(str(tmp), rows, FIELDNAMES)
    os.replace(tmp, path)


def ensure_sessions(
    sources: Sequence[Path],
    save_dir: Path,
    dates: Sequence[date],
    database: str,
    client_factory: Callable[[], AthenaClient],
    settled_before: date | None = None,
) -> tuple[list[dict[str, str]], list[date]]:
    """Session rows for ``dates``: local first, then fetch only the missing dates. Returns (rows, still_missing).

    A missing date on or after ``settled_before`` is refused: it would be saved as final while still loading.
    """
    loaded = load_daily(sources, SESSION_ARTIFACT, dates)
    if not loaded.missing:
        return loaded.rows, []
    unsettled = [d for d in loaded.missing if settled_before is not None and d >= settled_before]
    if unsettled:
        raise CohortError("refusing to fetch and save days that may still be loading: "
                          + ",".join(d.isoformat() for d in unsettled))
    LOGGER.info("Fetching %d missing playback-outcome dates: %s", len(loaded.missing),
                ",".join(d.isoformat() for d in loaded.missing))
    result = fetch_missing(client_factory(), QUERY_NAME, loaded.missing, artifact=SESSION_ARTIFACT, out_dir=save_dir,
                           params={"database": database}, fieldnames=SESSION_FIELDNAMES)
    reloaded = load_daily(sources, SESSION_ARTIFACT, dates)
    return reloaded.rows, reloaded.missing + [d for d in result.empty if d not in reloaded.missing]


def build_parser(config: AnalysisConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-date", type=date.fromisoformat, default=config.default_start_date)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--tenant", default=config.tenant)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--paths-config", type=Path, default=REPO_ROOT / "config" / "data_paths.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="list the dates that would be fetched; no AWS access, no output written")
    return parser


def run(args: argparse.Namespace, client_factory: Callable[[], AthenaClient] | None = None,
        database: str | None = None) -> int:
    resolver = YamlPathResolver.from_file(args.paths_config, REPO_ROOT)
    dates = date_range(args.start_date, args.end_date)
    out_dir = resolver.resolve_investigation_output_dir(SLUG, tenant=args.tenant)
    enriched_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, ENRICHED_ARTIFACT)
    built = build_cohort(read_enriched(enriched_path))
    cohort = built.members
    sources = default_sources(resolver, REPO_ROOT, args.tenant)
    if args.dry_run:
        missing = load_daily(sources, SESSION_ARTIFACT, dates).missing
        print(f"dry-run tenant={args.tenant} cohort_members={len(cohort)} would_fetch_dates="
              + (",".join(d.isoformat() for d in missing) or "none"))
        return 0
    rows, missing = ensure_sessions(
        sources, sources[0], dates, database or tenant_database(args.tenant),
        client_factory or (lambda: make_client(args.tenant)), settled_before=datetime.now(timezone.utc).date())
    coverage = attach_session_counts(cohort, rows)
    coverage = replace(coverage, skipped_rows=built.skipped_rows, bad_timestamp_rows=built.bad_timestamp_rows,
                       members_without_timestamp=built.members_without_timestamp)
    out_path = out_dir / resolver.format_range_filename(args.start_date, args.end_date, OUTPUT_ARTIFACT)
    write_cohort(out_path, cohort)
    print(f"wrote {len(cohort)} cohort members -> {out_path}")
    print(coverage.line(args.tenant))
    print("session_dates_without_data=" + (",".join(d.isoformat() for d in missing) or "none"))
    LOGGER.info("Wrote %d cohort members to %s", len(cohort), out_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    from src.lib.logging.bootstrap import init_logging

    init_logging("shaka-6001-build-6001-cohort")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    config = load_config(pre.parse_known_args(argv)[0].config)
    args = build_parser(config).parse_args(argv)
    try:
        return run(args)
    except (CohortError, FetchError, LocalDataError) as exc:
        LOGGER.error("build_6001_cohort failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
