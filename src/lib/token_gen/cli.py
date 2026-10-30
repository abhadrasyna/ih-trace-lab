"""CLI: ``python -m src.lib.token_gen.cli <householdID> [--expires-in 3600] [--env-file .env]``."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from src.lib.logging.bootstrap import init_logging
from src.lib.token_gen.client import (
    TokenError,
    create_silent_login_token,
    credentials_from_env,
    get_access_token,
)


def load_env_file(path: Path) -> dict[str, str]:
    """Parse simple ``KEY=VALUE`` lines (``#`` comments, optional quotes); a missing file yields ``{}``."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.removeprefix("export ").strip()] = value.strip().strip("'\"")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Synamedia silent-login token for a household.")
    parser.add_argument("household_id", help="householdID used as the token subject")
    parser.add_argument("--expires-in", type=int, default=3600, help="token lifetime in seconds")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="file holding the credentials")
    parser.add_argument("--json", action="store_true", dest="as_json", help="print the full JSON response")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    init_logging("token-gen")
    args = build_parser().parse_args(argv)
    env = {**load_env_file(args.env_file), **os.environ}
    try:
        client_id, client_secret = credentials_from_env(env)
        access_token = get_access_token(client_id, client_secret)
        result = create_silent_login_token(access_token, args.household_id, args.expires_in)
    except TokenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2))
        return 0
    token = result.get("token")
    if not token:
        print(f"error: response has no 'token' field; use --json to inspect it: {result}", file=sys.stderr)
        return 1
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
