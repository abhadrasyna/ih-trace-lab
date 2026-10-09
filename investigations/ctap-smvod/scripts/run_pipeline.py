#!/usr/bin/env python3
"""
Orchestrator for the CTAP/SM-VOD pipeline (BLUEPRINT.md Steps 2-6b), one
command per date instead of copy-pasting the "Quick reference" block by
hand. Runs, in order:

    Step 1b combine_lightstep_parts.py     -- combine split _01/_02... Lightstep CSV parts, if any
    Step 2  merge_ctap_smvod_csv.py       -- base 3-way merge
    Step 3  run_athena_playback_outcome.py -- Athena playback outcome (optional, --skip-step3)
    Step 4  run_athena_debug_events.py     -- Athena error/lifecycle    (optional, --skip-step4)
    Step 5  merge_session_outcome.py       -- final merge
    Step 6b extract_position_report.py     -- position-check view       (optional, --skip-step6b)
    Step 6e extract_error_report_1xxx_6xxx.py -- 1xxx/6xxx-only CSV   (optional, --skip-step6e)
    Step 6d analyze_webview_devices.py     -- WebView device reliability report (optional, --skip-step6d)
    Step 6f run_athena_error_eventdata.py  -- raw PLAYER_ERROR eventdata export (optional, --skip-error-eventdata)
    Step 6g flatten_error_eventdata.py     -- flat + per-error-code CSVs        (optional, --skip-error-eventdata)

Note: extract_position_report.py's --only-not-moved now defaults to on
(see its own docstring / BLUEPRINT.md Step 6b) -- pass --full-position-report
here if Step 6b's output needs to cover every session (e.g. before running
Step 6c/7 by hand afterward).

Step 1 (manually exporting the Lightstep CSVs into data/lightstep/) is NOT
automated here -- it has no live API (see README.md §6) and must already be
done before running this script. A high-volume day's export may come as
numbered parts (`YYYY-MM-DD_01_ctap.csv`, `YYYY-MM-DD_02_ctap.csv`, ...,
same for smvod/smvod-ts) instead of one whole-day file, if the Lightstep
span-sample cap (~1000 rows) was hit. Step 1b (combine_lightstep_parts.py)
runs automatically, every time, before Step 2's input check -- there is no
separate manual recombination command to remember. It is a safe no-op for
a date that has no numbered parts (nothing to combine). For a date that
does have numbered parts, it always (re)combines them into the canonical
file, even if one from a previous run is already there, so a part added,
re-exported, or removed since the last run is always reflected rather than
silently serving a stale combined file (see combine_lightstep_parts.py's
module docstring for why this doesn't rely on file timestamps).

Multi-tenant: with no --tenant, runs every tenant that has Lightstep input
for --date under data/lightstep/<TENANT>/ (inputs/outputs are namespaced per
tenant). --tenant <code> runs just that one. Within a tenant the pipeline
stops at the first step whose exit code is non-zero (no partial/stale data
downstream), but the remaining tenants still run; a per-tenant summary prints
at the end and the exit code is non-zero if any tenant failed.

Usage:
    python3 run_pipeline.py --date 18092026

    # Run a single tenant only:
    python3 run_pipeline.py --date 18092026 --tenant ZM

    # Print the exact commands this would run, in order, without running
    # anything (including no filesystem/Athena/network access):
    python3 run_pipeline.py --date 18092026 --dry-run

    # Skip both Athena enrichment steps (e.g. re-running Step 5/6b only
    # after data/athena/YYYY-MM-DD_session.csv and
    # data/athena/YYYY-MM-DD_debug_states.csv already
    # exist from a previous run):
    python3 run_pipeline.py --date 18092026 --skip-step3 --skip-step4

    # Skip Steps 3/4 automatically, but only for dates whose
    # data/athena/YYYY-MM-DD_session.csv /
    # data/athena/YYYY-MM-DD_debug_states.csv already
    # exist -- unlike --skip-step3/--skip-step4 (always skip), this checks
    # per-date and still fires Athena for any date missing that file:
    python3 run_pipeline.py --date 18092026 --skip-if-exists

    # Skip the optional position-check view:
    python3 run_pipeline.py --date 18092026 --skip-step6b

    # Skip the optional WebView device reliability report:
    python3 run_pipeline.py --date 18092026 --skip-step6d

    # Pass through Athena auth options to steps 3/4:
    python3 run_pipeline.py --date 18092026 --profile clarissa-insights-product --skip-auth-check
"""
import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from lib.runtime import investigation_data_dir, investigation_output_dir, snapshot_output_path
from lib.tenant_context import discover_tenants, require_lightstep_dir, resolve_tenant_context
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.run_pipeline")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _ddmmyyyy_to_iso(date_ddmmyyyy: str) -> str:
    """Converts 'DDMMYYYY' to 'YYYY-MM-DD' for the Athena scripts, which
    take an ISO partition date instead of this pipeline's DDMMYYYY
    convention.

    Raises:
        ValueError: If `date_ddmmyyyy` isn't valid DDMMYYYY.
    """
    return datetime.strptime(date_ddmmyyyy, "%d%m%Y").strftime("%Y-%m-%d")


def _tenant_dirs(tenant: str) -> dict[str, str]:
    """Tenant-scoped Lightstep input, Athena input and output folders."""
    return {
        "lightstep": str(investigation_data_dir("lightstep", tenant=tenant)),
        "athena": str(investigation_data_dir("athena", tenant=tenant)),
        "output": str(investigation_output_dir(tenant=tenant)),
    }


def _step2_lightstep_paths(date_ddmmyyyy: str, tenant: str) -> dict[str, str]:
    iso_date = _ddmmyyyy_to_iso(date_ddmmyyyy)
    lightstep_dir = _tenant_dirs(tenant)["lightstep"]
    return {
        "ctap": os.path.join(lightstep_dir, f"{iso_date}_ctap.csv"),
        "smvod": os.path.join(lightstep_dir, f"{iso_date}_smvod.csv"),
        "smvod-ts": os.path.join(lightstep_dir, f"{iso_date}_smvod-ts.csv"),
    }


def _ensure_step2_inputs_exist(date_ddmmyyyy: str, tenant: str) -> dict[str, str]:
    expected = _step2_lightstep_paths(date_ddmmyyyy, tenant)
    required_paths = [expected["ctap"], expected["smvod"]]
    missing = [path for path in required_paths if not os.path.exists(path)]
    if not missing:
        return expected
    raise FileNotFoundError(
        f"[{tenant}] Step 1 is still manual. Export the required Lightstep CSVs into "
        f"{_tenant_dirs(tenant)['lightstep']} using ISO-prefixed names "
        f"({os.path.basename(expected['ctap'])}, {os.path.basename(expected['smvod'])}; "
        f"optional span-samples file: {os.path.basename(expected['smvod-ts'])}). "
        f"Missing: {', '.join(os.path.basename(path) for path in missing)}"
    )


def _step3_output_path(date_ddmmyyyy: str, tenant: str) -> str:
    return os.path.join(_tenant_dirs(tenant)["athena"], f"{_ddmmyyyy_to_iso(date_ddmmyyyy)}_session.csv")


def _step4_output_path(date_ddmmyyyy: str, tenant: str) -> str:
    return os.path.join(_tenant_dirs(tenant)["athena"], f"{_ddmmyyyy_to_iso(date_ddmmyyyy)}_debug_states.csv")


def _step6f_output_path(date_ddmmyyyy: str, tenant: str) -> str:
    return os.path.join(_tenant_dirs(tenant)["athena"], f"{_ddmmyyyy_to_iso(date_ddmmyyyy)}_error_eventdata.csv")


def _build_steps(args, date_iso: str, tenant: str):
    """Returns the ordered list of (step_label, command_list, skip) tuples
    for one tenant's pipeline run, given parsed CLI `args`."""
    py = sys.executable
    dirs = _tenant_dirs(tenant)
    lightstep_dir, athena_dir, output_dir = dirs["lightstep"], dirs["athena"], dirs["output"]
    snap = lambda artifact: snapshot_output_path(args.date, artifact, output_dir=output_dir)  # noqa: E731

    athena_common = []
    if args.profile:
        athena_common += ["--profile", args.profile]
    if args.skip_auth_check:
        athena_common += ["--skip-auth-check"]
    if args.force:
        athena_common += ["--force"]
    athena_common += ["--tenant", tenant, "--output-dir", athena_dir]

    # --skip-if-exists is opt-in and per-date: unlike --skip-step3/--skip-step4
    # (always skip, regardless of file state), this only skips Athena for a
    # date whose enrichment CSV is already present -- a date still missing
    # it fires Athena as normal. Default stays "always re-run Athena" so a
    # plain run never silently serves stale enrichment data.
    step3_path = _step3_output_path(args.date, tenant)
    step4_path = _step4_output_path(args.date, tenant)
    step6f_path = _step6f_output_path(args.date, tenant)
    skip3_existing = args.skip_if_exists and os.path.exists(step3_path)
    skip4_existing = args.skip_if_exists and os.path.exists(step4_path)

    step3_label = "Step 3 - Athena playback outcome (run_athena_playback_outcome.py)"
    if skip3_existing:
        step3_label += f" [skipped: {step3_path} already exists]"
    step4_label = "Step 4 - Athena error/lifecycle (run_athena_debug_events.py)"
    if skip4_existing:
        step4_label += f" [skipped: {step4_path} already exists]"

    steps = [
        (
            "Step 1b - combine split Lightstep CSV parts (combine_lightstep_parts.py)",
            [py, os.path.join(SCRIPT_DIR, "combine_lightstep_parts.py"),
             "--date", date_iso, "--input-dir", lightstep_dir],
            False,
        ),
        (
            "Step 2 - base merge (merge_ctap_smvod_csv.py)",
            [py, os.path.join(SCRIPT_DIR, "merge_ctap_smvod_csv.py"), "--date", args.date,
             "--input-dir", lightstep_dir, "--out", snap("setupsession"), "--tenant", tenant],
            False,
        ),
        (
            step3_label,
            [py, os.path.join(SCRIPT_DIR, "run_athena_playback_outcome.py"), "--date", date_iso] + athena_common,
            args.skip_step3 or skip3_existing,
        ),
        (
            step4_label,
            [py, os.path.join(SCRIPT_DIR, "run_athena_debug_events.py"), "--date", date_iso] + athena_common,
            args.skip_step4 or skip4_existing,
        ),
        (
            "Step 5 - final merge (merge_session_outcome.py)",
            [py, os.path.join(SCRIPT_DIR, "merge_session_outcome.py"), "--date", args.date,
             "--input-dir", athena_dir, "--report", snap("setupsession"),
             "--out", snap("setupsession_with_outcome")],
            False,
        ),
        (
            "Step 6b - position-check view (extract_position_report.py)",
            [py, os.path.join(SCRIPT_DIR, "extract_position_report.py"), "--date", args.date,
             "--input", snap("setupsession_with_outcome"), "--out", snap("position_report")]
            + (["--no-only-not-moved"] if args.full_position_report else []),
            args.skip_step6b,
        ),
        (
            "Step 6e - 1xxx/6xxx error report (extract_error_report_1xxx_6xxx.py)",
            [py, os.path.join(SCRIPT_DIR, "extract_error_report_1xxx_6xxx.py"), "--date", args.date,
             "--output-dir", output_dir],
            args.skip_step6e,
        ),
        (
            "Step 6d - WebView device reliability report (analyze_webview_devices.py)",
            [py, os.path.join(SCRIPT_DIR, "analyze_webview_devices.py"), "--date", args.date,
             "--input-dir", output_dir, "--output-dir", output_dir],
            args.skip_step6d,
        ),
        (
            "Step 6f - raw PLAYER_ERROR eventdata export (run_athena_error_eventdata.py)",
            [py, os.path.join(SCRIPT_DIR, "run_athena_error_eventdata.py"), "--date", date_iso] + athena_common,
            args.skip_error_eventdata,
        ),
        (
            "Step 6g - flatten error eventdata (flatten_error_eventdata.py)",
            [py, os.path.join(SCRIPT_DIR, "flatten_error_eventdata.py"), "--input", step6f_path,
             "--date", date_iso, "--out-dir", os.path.join(output_dir, "error_eventdata_flat"),
             "--split-by-errorcode"],
            args.skip_error_eventdata,
        ),
    ]
    return steps


def _run_tenant(args, date_iso: str, tenant: str) -> str | None:
    """Runs every step for `tenant`; returns None on success or a failure description."""
    for step_index, (label, command, skip) in enumerate(_build_steps(args, date_iso, tenant)):
        if skip:
            print(f"==> [{tenant}] {label}: SKIPPED", file=sys.stderr)
            continue
        print(f"==> [{tenant}] {label}", file=sys.stderr)
        print(f"    $ {' '.join(command)}", file=sys.stderr)
        result = subprocess.run(command)
        if result.returncode != 0:
            return f"'{label}' exited with code {result.returncode}"
        if step_index == 0:
            # Step 1b (always _build_steps' first entry) may have just created
            # the canonical _ctap.csv/_smvod.csv files from numbered parts --
            # validate *after* it runs, not before, so a date that only has
            # parts (no whole-day file yet) isn't rejected before Step 1b gets
            # a chance to produce them. Keyed on position, not the label text,
            # so renaming Step 1b's label can't silently drop this check.
            try:
                _ensure_step2_inputs_exist(args.date, tenant)
            except FileNotFoundError as exc:
                return str(exc)
    return None


def _select_tenants(requested: str | None, date_iso: str) -> list[str]:
    """`--tenant` -> that one tenant (validated); otherwise every tenant with input for the date.

    Raises:
        ValueError / FileNotFoundError: unknown tenant, missing folder, or no tenant has input.
    """
    if requested:
        code = resolve_tenant_context(requested).code
        require_lightstep_dir(code)
        return [code]
    tenants = discover_tenants(date_iso)
    if not tenants:
        root = investigation_data_dir("lightstep")
        raise FileNotFoundError(f"No tenant has Lightstep input for {date_iso} under {root}/<TENANT>/")
    return tenants


def main():
    init_logging("ctap-smvod-run_pipeline")
    LOGGER.info("Starting run_pipeline")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 18092026")
    ap.add_argument("--tenant", default=None,
                    help="Tenant code from config/tenants.yaml; default: every tenant with Lightstep input for --date")
    ap.add_argument("--skip-step3", action="store_true", help="Skip Step 3 (Athena playback outcome)")
    ap.add_argument("--skip-step4", action="store_true", help="Skip Step 4 (Athena error/lifecycle)")
    ap.add_argument(
        "--skip-if-exists", action="store_true",
        help="Opt-in, per-date auto-skip: skip Step 3 if "
             "data/athena/YYYY-MM-DD_session.csv already exists, and/or Step 4 "
             "if data/athena/YYYY-MM-DD_debug_states.csv already exists, instead of "
             "always re-firing Athena (the default). A date still missing "
             "either file fires Athena for that step as normal.")
    ap.add_argument(
        "--force", action="store_true",
        help="Passed through to Steps 3/4: re-run Athena even if the output CSV already has data "
             "(by default each Athena step skips itself when its CSV exists)")
    ap.add_argument("--skip-step6b", action="store_true", help="Skip Step 6b (position-check view)")
    ap.add_argument("--skip-step6e", action="store_true",
                     help="Skip Step 6e (1xxx/6xxx error report CSV)")
    ap.add_argument("--skip-step6d", action="store_true",
                     help="Skip Step 6d (WebView device reliability report)")
    ap.add_argument("--skip-error-eventdata", action="store_true",
                     help="Skip Steps 6f/6g (raw PLAYER_ERROR eventdata export + flatten)")
    ap.add_argument(
        "--full-position-report", action="store_true",
        help="Pass --no-only-not-moved to Step 6b, so output/YYYY-MM-DD_position_report.csv "
             "covers every session instead of extract_position_report.py's new "
             "on-by-default --only-not-moved filter -- needed if you'll run Step 6c/7 "
             "(filter_error_code_report.py/correlate_cdn_ips.py) afterward, which both "
             "expect the full session set")
    ap.add_argument("--profile", default=None, help="AWS SSO profile, passed through to Steps 3/4")
    ap.add_argument("--skip-auth-check", action="store_true", help="Passed through to Steps 3/4")
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Print the commands that would run, in order, and exit -- no "
             "filesystem/Athena/network access")
    args = ap.parse_args()

    try:
        date_iso = _ddmmyyyy_to_iso(args.date)
    except ValueError:
        print(f"ERROR: --date must be DDMMYYYY, got '{args.date}'", file=sys.stderr)
        sys.exit(1)

    try:
        tenants = _select_tenants(args.tenant, date_iso)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        for tenant in tenants:
            for label, command, skip in _build_steps(args, date_iso, tenant):
                marker = "(skipped)" if skip else ""
                print(f"# [{tenant}] {label} {marker}".rstrip())
                print(" ".join(command))
        LOGGER.info("Completed run_pipeline dry_run date=%s tenants=%s", args.date, ",".join(tenants))
        return

    failures: dict[str, str] = {}
    for tenant in tenants:
        LOGGER.info("Running tenant=%s date=%s", tenant, args.date)
        failure = _run_tenant(args, date_iso, tenant)
        if failure:
            failures[tenant] = failure
            LOGGER.error("Tenant failed tenant=%s date=%s: %s", tenant, args.date, failure)

    print(f"\nPipeline summary for {args.date}:", file=sys.stderr)
    for tenant in tenants:
        print(f"  {tenant}: {'FAILED - ' + failures[tenant] if tenant in failures else 'OK'}", file=sys.stderr)
    if failures:
        print(
            "\nPIPELINE FAILED for tenant(s): " + ", ".join(failures) + ". Fix the error above and re-run "
            "with --tenant <code> (pass --skip-step3/--skip-step4/--skip-step6b to resume past "
            "already-completed steps).",
            file=sys.stderr)
        sys.exit(1)

    print(f"\nPipeline complete for {args.date}.", file=sys.stderr)
    LOGGER.info("Completed run_pipeline date=%s tenants=%s", args.date, ",".join(tenants))


if __name__ == "__main__":
    main()
