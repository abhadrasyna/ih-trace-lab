"""Tiny loader for Athena SQL templates stored in the repo query catalog."""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class QueryCatalog:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(__file__).resolve().parents[3]
        self._catalog_dir = self._root / "queries" / "athena"

    def path_for(self, key: str) -> Path:
        return self._catalog_dir / f"{key}.sql"

    def load(self, key: str) -> str:
        path = self.path_for(key)
        if not path.is_file():
            raise FileNotFoundError(f"No Athena catalog entry found for {key!r} at {path}")
        return path.read_text(encoding="utf-8")

    def render(self, key: str, params: Mapping[str, str]) -> str:
        template = self.load(key)
        missing = {name for name in _PLACEHOLDER_RE.findall(template) if name not in params}
        if missing:
            raise KeyError(f"Catalog query {key!r} is missing params: {sorted(missing)}")
        return _PLACEHOLDER_RE.sub(lambda match: str(params[match.group(1)]), template)


def quote_sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def comma_join_quoted(values: list[str]) -> str:
    return ", ".join(quote_sql_literal(value) for value in values)
