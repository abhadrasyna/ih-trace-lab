"""mDRM license-chain quality report for one OpCo and day: statuses, failures, retries, fcId consistency, part overlap.

Reads only the saved Lightstep exports (no Athena or Lightstep calls):
  <drm-dir>/<date>_mdrmfe.csv, _mdrm-lrm.csv, _mdrm-cdm-{widevine,fairplay,playready}.csv (+ hourly parts)
Writes <base>/<OPCO>/drm-analysis/<date>_mdrm_quality.md and csv/<date>_mdrm_quality_failures.csv.

Usage:
  python investigations/ctap-smvod/scripts/analyze_mdrm_quality.py --opco ZA --date 2026-10-23
"""
from __future__ import annotations

import argparse
import csv
import logging
from dataclasses import asdict, fields
from pathlib import Path

from lib.drm_exports import (
    FAIRPLAY,
    LRM,
    MDRMFE,
    PLAYREADY,
    WIDEVINE,
    export_paths,
    read_cdm,
    read_fcids_by_part,
    read_lrm,
    read_mdrmfe,
)
from lib.drm_output import drm_analysis_dir, drm_csv_dir
from lib.drm_quality import (
    FailedRequest,
    duplicate_fcids_across_parts,
    failing_requests,
    fcid_chain,
    layer_overlap,
    repeat_failures,
    requests_per_key,
    retry_sessions,
    status_counts,
    whole_day_with_parts,
)

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.analyze_mdrm_quality")
DEFAULT_BASE = Path(__file__).resolve().parents[1] / "output"
DEFAULT_DRM_BASE = Path(__file__).resolve().parents[1] / "data" / "lightstep"
KINDS = (MDRMFE, LRM, WIDEVINE, FAIRPLAY, PLAYREADY)
TOP_N = 10


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(r) + " |" for r in rows)
    return lines


def overlap_warnings(drm_dir: Path, date: str) -> list[str]:
    """Whole-day-plus-parts warnings and duplicate ``fcId`` counts across files, per export kind."""
    out: list[str] = []
    for kind in KINDS:
        paths = export_paths(drm_dir, date, kind)
        if not paths:
            continue
        warning = whole_day_with_parts([p.name for p in paths], date, kind)
        if warning:
            out.append(warning)
        dups = duplicate_fcids_across_parts(read_fcids_by_part(drm_dir, date, kind))
        if dups:
            sample = next(iter(dups))
            out.append(f"{kind}: {len(dups)} fcId(s) appear in more than one file (for example {sample} in {dups[sample]})")
    return out


def render_markdown(opco: str, date: str, drm_dir: Path) -> tuple[str, list[FailedRequest]]:
    mdrmfe, lrm, cdm = read_mdrmfe(drm_dir, date), read_lrm(drm_dir, date), read_cdm(drm_dir, date)
    failures = failing_requests(mdrmfe, lrm)
    chain = fcid_chain(mdrmfe, lrm, cdm)
    lines = [f"# mDRM license-chain quality — {opco} — {date}", "", "## Status codes per export", ""]
    lines += _table(["export", "drm_type", "status", "rows"],
                    [[s.export, s.drm_type, s.status, str(s.count)] for s in status_counts(mdrmfe, lrm, cdm)])
    overlap = layer_overlap(failures)
    lines += ["", f"## Failing requests ({len(failures)} distinct fcId)", "",
              f"Failing at both layers: {overlap['mdrmfe+lrm']}; mdrmfe only: {overlap['mdrmfe']}; LRM only: {overlap['lrm']}. "
              f"Full list with device, household, content and user agent: `csv/{date}_mdrm_quality_failures.csv`.", ""]
    for dim, items in repeat_failures(failures).items():
        lines.append(f"- Repeat failures by `{dim}`: " + (", ".join(f"{k[:12]}… ×{n}" for k, n in items[:TOP_N]) or "none"))
    lines += ["", "## Requests per session and household", "",
              "Distinct `fcId` count; sessions with more than one are retries or re-acquisitions.", ""]
    for key in ("session_id", "household_id"):
        hist = requests_per_key(mdrmfe, key)
        lines.append(f"- Per `{key}`: " + (", ".join(f"{n} request(s): {c}" for n, c in hist.items()) or "none"))
    lines += ["", f"Sessions with retries: {len(retry_sessions(mdrmfe))}."]
    lines += ["", "## fcId consistency", ""]
    lines += _table(["check", "count"], [
        ["fcId in mdrmfe / LRM / CDM", f"{chain.mdrmfe_total} / {chain.lrm_total} / {chain.cdm_total}"],
        ["in mdrmfe, missing from LRM", f"{chain.mdrmfe_not_in_lrm} (of which mdrmfe 201: {chain.mdrmfe_not_in_lrm_ok})"],
        ["in mdrmfe, missing from CDM", str(chain.mdrmfe_not_in_cdm)],
        ["in LRM, missing from mdrmfe", str(chain.lrm_not_in_mdrmfe)],
        ["in CDM, missing from mdrmfe", str(chain.cdm_not_in_mdrmfe)],
        ["deviceId differs between mdrmfe and LRM", str(len(chain.device_mismatches))],
    ])
    lines += ["", "## Export file overlap", ""]
    warnings = overlap_warnings(drm_dir, date)
    lines += [f"- {w}" for w in warnings] or ["No whole-day file alongside parts and no `fcId` repeated across files."]
    return "\n".join(lines) + "\n", failures


def write_outputs(out_dir: Path, opco: str, date: str, markdown: str, failures: list[FailedRequest]) -> tuple[Path, Path]:
    csv_dir = drm_csv_dir(out_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{date}_mdrm_quality.md"
    csv_path = csv_dir / f"{date}_mdrm_quality_failures.csv"
    md_path.write_text(markdown, encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(FailedRequest)])
        writer.writeheader()
        writer.writerows(asdict(f) for f in failures)
    return md_path, csv_path


def run(opco: str, date: str, base: Path, drm_dir: Path) -> list[FailedRequest]:
    markdown, failures = render_markdown(opco, date, drm_dir)
    write_outputs(drm_analysis_dir(base, opco), opco, date, markdown, failures)
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opco", required=True, help="OpCo folder, e.g. ZA")
    ap.add_argument("--date", required=True, help="day YYYY-MM-DD")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE, help="output root holding <OPCO>/ folders")
    ap.add_argument("--drm-dir", type=Path, default=None, help="folder with the saved mDRM exports (default data/lightstep/<OPCO>)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

    from src.lib.logging.bootstrap import init_logging

    init_logging("ctap-smvod-analyze_mdrm_quality")
    args = parse_args(argv)
    failures = run(args.opco, args.date, args.base, args.drm_dir or DEFAULT_DRM_BASE / args.opco)
    LOGGER.info("%s %s: %d failing fcId(s)", args.opco, args.date, len(failures))


if __name__ == "__main__":
    main()
