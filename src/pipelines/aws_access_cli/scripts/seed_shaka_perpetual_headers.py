"""One-time migration: seed this repo's weekly/monthly Shaka perpetual files' column order.

The pre-migration `aws-access-cli` repo's weekly/monthly Shaka error files
(`output/<TENANT>/{weekly,monthly}/shaka_error_{hhid,sessions}.csv`) have already accumulated
months of history, so any error code discovered only once -- mid-history -- keeps whatever
column position it was first assigned back then. This repo's equivalent perpetual files
(`output/<TENANT>/{weekly,monthly}/shaka-error-{hhid,session}.csv`, see
`format_perpetual_filename`) start empty, so `pivot_error_counts` would instead sort any codes
that are new to *this* repo's file alphabetically -- which only matches the legacy column order
by coincidence, since the legacy order reflects *when* each code first appeared historically, not
alphabetical order (see `pivot_error_counts`'s docstring and `shaka_errors.py::KNOWN_ERROR_CODES`).

This script copies over the legacy file's *header only* (no data rows) the first time this
repo's perpetual file is created, so `_existing_shaka_pivot_columns` picks up the legacy-established
column order on this repo's very first write -- without copying any historical data. It is
idempotent and safe to rerun: it never touches a perpetual file this repo has already created.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.lib.csv_io.csv_file import CsvFileWriter
from src.lib.logging.bootstrap import init_logging
from src.pipelines.aws_access_cli.runtime import make_path_resolver, repo_root
from src.pipelines.aws_access_cli.tenants import TENANTS_BY_CODE

# artifact (this repo's perpetual filename stem) -> legacy repo's filename stem.
_ARTIFACT_TO_LEGACY_STEM = {
    "shaka-error-hhid": "shaka_error_hhid",
    "shaka-error-session": "shaka_error_sessions",
}
_PERIOD_DIRS = ("weekly", "monthly")


def _read_legacy_header(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    # utf-8-sig strips a leading BOM (e.g. from Excel/pandas-exported CSVs) instead of folding it
    # into the first column name, which would silently corrupt that column across every future run.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), None)
    return header or None


def seed_headers(*, legacy_root: Path, output_root: Path, tenant_codes: list[str], dry_run: bool) -> list[str]:
    """Seeds every (tenant, period, artifact) perpetual file that doesn't exist yet in
    `output_root` but does in `legacy_root`. Returns one human-readable action line per
    (tenant, period, artifact) combination, in the order processed.

    Raises:
        NotADirectoryError: If `legacy_root` doesn't exist -- a typo'd or wrong `--legacy-root`
            must fail loudly rather than silently logging every combination as "no legacy file"
            and letting the pipeline create alphabetically-sorted perpetual files that this
            script can then never retroactively fix (it only ever seeds a file that doesn't
            exist yet).
    """
    if not legacy_root.is_dir():
        raise NotADirectoryError(f"--legacy-root {legacy_root} does not exist or is not a directory")
    resolver = make_path_resolver()
    writer = CsvFileWriter()
    actions: list[str] = []
    for tenant_code in tenant_codes:
        for period_dir in _PERIOD_DIRS:
            for artifact, legacy_stem in _ARTIFACT_TO_LEGACY_STEM.items():
                new_path = output_root / tenant_code / period_dir / resolver.format_perpetual_filename(artifact)
                legacy_path = legacy_root / tenant_code / period_dir / f"{legacy_stem}.csv"
                label = f"{tenant_code}/{period_dir}/{artifact}"
                if new_path.is_file():
                    actions.append(f"SKIP  (already exists)  {label} -> {new_path}")
                    continue
                header = _read_legacy_header(legacy_path)
                if header is None:
                    actions.append(f"SKIP  (no legacy file)  {label} -> {legacy_path}")
                    continue
                if dry_run:
                    actions.append(f"WOULD SEED  {label}  header={header} -> {new_path}")
                    continue
                new_path.parent.mkdir(parents=True, exist_ok=True)
                writer.write_rows(str(new_path), [], header)
                actions.append(f"SEEDED  {label}  header={header} -> {new_path}")
    return actions


def main(argv: list[str] | None = None) -> int:
    init_logging("aws-access-cli-seed-shaka-perpetual-headers")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-root",
        default="/Users/abhadra/github_copilot/aws-access-cli/output",
        help="The pre-migration aws-access-cli repo's output/ directory to copy header order from.",
    )
    parser.add_argument("--output-dir", default="output", help="This repo's output directory (relative to the repo root unless absolute).")
    parser.add_argument("--tenant", default=None, choices=sorted(TENANTS_BY_CODE), help="Seed only this tenant; default is all configured tenants.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be seeded without writing any files.")
    args = parser.parse_args(argv)

    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = repo_root() / output_root
    tenant_codes = [args.tenant] if args.tenant else sorted(TENANTS_BY_CODE)

    actions = seed_headers(legacy_root=Path(args.legacy_root), output_root=output_root, tenant_codes=tenant_codes, dry_run=args.dry_run)
    for action in actions:
        print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
