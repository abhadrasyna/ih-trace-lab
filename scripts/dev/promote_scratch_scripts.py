#!/usr/bin/env python3
"""Manually promote stable scratch scripts into ``scripts/dev/``.

The default age threshold is 30 days: long enough that a surviving scratch script has
proven reusable, short enough that a monthly promotion pass catches it before the
registry grows stale with effectively-production scripts still listed as scratch.
"""
from __future__ import annotations

import argparse
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    from generate_scripts_registry import (
        SCRIPT_EXTENSIONS,
        build_registry,
        extract_purpose,
        extract_scratch_date,
        find_scripts,
    )
else:
    from .generate_scripts_registry import (
        SCRIPT_EXTENSIONS,
        build_registry,
        extract_purpose,
        extract_scratch_date,
        find_scripts,
    )

DEFAULT_MIN_AGE_DAYS = 30
__all__ = ["DEFAULT_MIN_AGE_DAYS", "find_promotion_candidates", "main", "promote"]


def find_promotion_candidates(scratch_dir: Path, min_age_days: int) -> list[Path]:
    """Return eligible scratch scripts, oldest first."""
    if min_age_days < 0:
        raise ValueError("min_age_days must be >= 0")

    today = datetime.now(timezone.utc).date()
    candidates: list[tuple[date, Path]] = []
    for relative_path in find_scripts(scratch_dir.parent, scratch_dir.name):
        script_path = scratch_dir.parent / relative_path
        date_text = extract_scratch_date(relative_path)
        if date_text is None:
            continue
        try:
            script_date = date.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError(f"{relative_path} has an invalid scratch date: {date_text}") from exc
        if (today - script_date).days >= min_age_days:
            candidates.append((script_date, script_path))
    candidates.sort(key=lambda item: (item[0], item[1].name))
    return [path for _, path in candidates]


def promote(script_path: Path, dest_dir: Path) -> Path:
    """Move one scratch script into ``dest_dir`` and regenerate ``SCRIPTS.md``."""
    dest_dir = dest_dir.resolve()
    root = dest_dir.parents[1]
    scratch_dir = (root / "scratch").resolve()
    script_resolved = script_path.resolve()
    if not script_resolved.exists():
        raise ValueError(f"{script_path} does not exist")
    if not script_resolved.is_file() or script_resolved.suffix not in SCRIPT_EXTENSIONS:
        raise ValueError(f"{script_path} is not a scratch script")
    if scratch_dir not in script_resolved.parents:
        raise ValueError(f"{script_path} is not under {scratch_dir}")

    registry_path = root / "SCRIPTS.md"
    prior_registry = registry_path.read_text(encoding="utf-8") if registry_path.exists() else None
    temp_path = root / ".SCRIPTS.md.tmp"
    destination = dest_dir / script_resolved.name
    subprocess.run(["git", "-C", str(root), "mv", str(script_resolved), str(destination)], check=True)
    try:
        temp_path.write_text(build_registry(root), encoding="utf-8")
        temp_path.replace(registry_path)
        subprocess.run(["git", "-C", str(root), "add", str(registry_path)], check=True)
    except Exception as exc:
        rollback_errors: list[str] = []
        try:
            subprocess.run(["git", "-C", str(root), "mv", str(destination), str(script_resolved)], check=True)
        except subprocess.CalledProcessError as rollback_exc:
            rollback_errors.append(f"rollback move failed: {rollback_exc}")
        try:
            if prior_registry is None:
                if registry_path.exists():
                    registry_path.unlink()
            else:
                registry_path.write_text(prior_registry, encoding="utf-8")
        except OSError as restore_exc:
            rollback_errors.append(f"registry restore failed: {restore_exc}")
        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise RuntimeError(f"promotion failed and rollback was incomplete: {details}") from exc
        raise
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return destination


def main() -> None:
    """List promotion candidates or promote exactly one scratch script."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--list",
        action="store_true",
        help="List scratch scripts old enough to consider for promotion.",
    )
    mode.add_argument(
        "--script",
        type=Path,
        help="Promote exactly this scratch script into scripts/dev/.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_MIN_AGE_DAYS,
        help=f"Minimum scratch-script age in days for --list (default: {DEFAULT_MIN_AGE_DAYS}).",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    scratch_dir = root / "scratch"
    dest_dir = root / "scripts" / "dev"

    if args.list:
        for candidate in find_promotion_candidates(scratch_dir, args.days):
            relative_path = candidate.relative_to(root)
            date_text = extract_scratch_date(relative_path) or "—"
            purpose = extract_purpose(candidate) or "—"
            print(f"{date_text}\t{relative_path}\t{purpose}")
        return

    destination = promote(args.script, dest_dir)
    print(f"Promoted {args.script} -> {destination.relative_to(root)}")


if __name__ == "__main__":
    main()
