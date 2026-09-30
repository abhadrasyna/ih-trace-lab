#!/usr/bin/env python3
"""Resolve one tenant identifier into a system-specific query context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tenant_registry import AthenaQueryTarget, LightstepGoQueryTarget, MatisseQueryTarget, QueryTarget, TenantRegistry


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for tenant resolution."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=("lightstep_go", "matisse", "athena"), required=True)
    parser.add_argument("--tenant", required=True)
    args = parser.parse_args(argv)

    registry = TenantRegistry()
    targets: dict[str, QueryTarget] = {
        "lightstep_go": LightstepGoQueryTarget(),
        "matisse": MatisseQueryTarget(),
        "athena": AthenaQueryTarget(),
    }
    try:
        tenant = registry.get(args.tenant)
        print(json.dumps(targets[args.system].build_context(tenant), sort_keys=True))
    except (KeyError, ValueError) as exc:
        print(exc.args[0], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
