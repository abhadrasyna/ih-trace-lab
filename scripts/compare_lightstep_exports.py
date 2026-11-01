"""Compare hand-exported Lightstep CSVs with API-generated ones for one date, by key set.

Usage:
    python3 scripts/compare_lightstep_exports.py --manual-dir investigations/ctap-smvod/data/lightstep/ZA \
        --generated-dir investigations/ctap-smvod/data/lightstep/ZA/check_script --date 2026-10-29
Keys are all non-stat columns (``sessionId`` for smvod-ts); a leading apostrophe is ignored. Exit 1 if a kind has no files on either side.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.lightstep_compare import compare_kind, find_files, format_report, read_rows  # noqa: E402
from scripts.lib.lightstep_export_kinds import KINDS  # noqa: E402
from src.lib.logging.bootstrap import init_logging  # noqa: E402

LOGGER = logging.getLogger("scripts.compare_lightstep_exports")


def main(argv: Sequence[str] | None = None) -> int:
    init_logging("compare-lightstep-exports")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manual-dir", type=Path, required=True)
    ap.add_argument("--generated-dir", type=Path, required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--kinds", nargs="+", default=list(KINDS), choices=list(KINDS))
    args = ap.parse_args(argv)
    results, ok = [], True
    for kind in args.kinds:
        manual, generated = find_files(args.manual_dir, args.date, kind), find_files(args.generated_dir, args.date, kind)
        if not manual or not generated:
            LOGGER.error("%s: manual files=%d generated files=%d", kind, len(manual), len(generated))
            ok = False
            continue
        LOGGER.info("comparing %s: %d manual file(s) vs %d generated file(s)", kind, len(manual), len(generated))
        results.append(compare_kind(kind, read_rows(manual), read_rows(generated)))
    print(format_report(results))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
