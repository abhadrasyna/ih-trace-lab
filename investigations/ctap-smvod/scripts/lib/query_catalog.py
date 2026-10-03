"""Helpers for loading parameterized Athena SQL from the root query catalog."""
from __future__ import annotations

import re
from pathlib import Path

from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap

ATHENA_QUERY_DIR = REPO_ROOT / "queries" / "athena"
PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def query_path(slug: str) -> Path:
    return ATHENA_QUERY_DIR / f"{slug}.sql"


def load_query_template(slug: str) -> str:
    path = query_path(slug)
    if not path.is_file():
        raise FileNotFoundError(f"query catalog entry not found: {path}")
    return path.read_text(encoding="utf-8")


def render_query(slug: str, params: dict[str, str]) -> str:
    template = load_query_template(slug)
    placeholders = set(PLACEHOLDER_RE.findall(template))
    missing = sorted(name for name in placeholders if name not in params)
    if missing:
        raise ValueError(f"missing query parameters for {slug}: {', '.join(missing)}")

    rendered = template
    for name, value in params.items():
        rendered = rendered.replace(f"{{{{{name}}}}}", value)

    unresolved = sorted(set(PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        raise ValueError(f"unresolved query parameters for {slug}: {', '.join(unresolved)}")
    return rendered
