#!/usr/bin/env python3
"""Harvest Lightstep markdown templates into the repo query catalog."""

from __future__ import annotations

import argparse
import logging
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from logs.setup_logging import setup_logging

DEFAULT_SOURCE = Path("/Users/abhadra/github_copilot/applauseInvestigation/knowledge/lightstep-query-templates.md")
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
HEADING_RE = re.compile(r"(?m)^(##|###)\s+(.+)$")
PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")
SERVICE_RE = re.compile(r'service(?:\.name)?\s*==\s*"([^"]+)"')
LOGGER = logging.getLogger("scripts.dev.harvest_lightstep_query_catalog")


@dataclass(frozen=True)
class RawTemplate:
    """Parsed template data from the reference markdown."""

    title: str
    tql: str
    purpose: str | None
    tool: str | None
    save_exports_as: str | None


@dataclass(frozen=True)
class CatalogEntry:
    """Rendered catalog entry."""

    title: str
    slug: str
    tql: str
    purpose: str | None
    tool: str | None
    save_exports_as: str | None
    service_tool: str
    source: Path


def extract_templates(markdown_path: Path) -> list[RawTemplate]:
    """Return one template for each ##/### section with a fenced code block."""
    text = markdown_path.read_text(encoding="utf-8")
    templates: list[RawTemplate] = []
    for title, body in _split_sections(text):
        tql = _extract_code_block(body)
        if tql is None:
            LOGGER.info("Skipping section without code block: %s", title)
            continue
        templates.append(
            RawTemplate(
                title=_clean_title(title),
                tql=_reformat_placeholders(tql.strip()),
                purpose=_extract_labeled_value(body, "Purpose"),
                tool=_extract_tool(body),
                save_exports_as=_extract_save_path(body),
            )
        )
    return templates


def slugify(title: str) -> str:
    """Convert a markdown heading into a stable kebab-case slug."""
    cleaned = _slug_title_source(_clean_title(title))
    collapsed = re.sub(r"(?<=\w)[-/](?=\w)", "", cleaned).replace("×", " ")
    stripped = re.sub(r"[`'\"“”‘’]", "", collapsed).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stripped)
    return re.sub(r"-{2,}", "-", slug).strip("-")


def build_catalog(path: Path) -> list[CatalogEntry]:
    """Build the sorted catalog entries for one Lightstep template source file."""
    entries = [
        CatalogEntry(
            title=template.title,
            slug=slugify(template.title),
            tql=template.tql,
            purpose=template.purpose,
            tool=template.tool,
            save_exports_as=template.save_exports_as,
            service_tool=_service_tool_label(template.tql, template.tool),
            source=path,
        )
        for template in extract_templates(path)
    ]
    return sorted(entries, key=lambda entry: entry.slug)


def write_catalog(root: Path, catalog: list[CatalogEntry]) -> None:
    """Write the per-template markdown files and the Lightstep index."""
    out_dir = root / "queries" / "lightstep"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(out_dir.glob("*.md")):
        if path.name != "index.md":
            path.unlink()
    for entry in catalog:
        (out_dir / f"{entry.slug}.md").write_text(_render_template_file(entry), encoding="utf-8")
    (out_dir / "index.md").write_text(_render_index(catalog), encoding="utf-8")


def main() -> None:
    """Parse the source markdown, write the catalog, and print the count."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Source markdown file to harvest.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root for generated query files.",
    )
    args = parser.parse_args()

    setup_logging(to_file=False)
    source = args.source.resolve()
    root = args.root.resolve()
    catalog = build_catalog(source)
    write_catalog(root, catalog)
    print(f"Wrote {len(catalog)} Lightstep templates to {root / 'queries' / 'lightstep'}")


def _split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(2).strip(), text[match.end() : end].strip()))
    return sections


def _extract_code_block(body: str) -> str | None:
    match = re.search(r"(?ms)^\s*```[^\n]*\n(.*?)\n\s*```", body)
    return match.group(1) if match else None


def _extract_labeled_value(body: str, label: str) -> str | None:
    prefix = f"**{label}:**"
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        collected = [line[len(prefix) :].strip()]
        for continuation in lines[index + 1 :]:
            stripped = continuation.strip()
            if not stripped or stripped.startswith(("**", "### ", "## ", "Tool:")):
                break
            collected.append(stripped)
        value = " ".join(part for part in collected if part)
        return _normalize_inline_whitespace(_strip_wrapping_ticks(value))
    return None


def _extract_tool(body: str) -> str | None:
    explicit = re.search(r"(?m)^Tool:\s*(.+)$", body)
    if explicit:
        tool_text = explicit.group(1).strip()
        backticked = re.search(r"`([^`]+)`", tool_text)
        return backticked.group(1) if backticked else tool_text.rstrip(".")
    before_code = body.split("```", maxsplit=1)[0]
    numbered = re.search(r"(?m)^\d+\.\s+`([^`]+)`", before_code)
    if numbered:
        return numbered.group(1)
    return "query_timeseries" if "spans " in body else None


def _extract_save_path(body: str) -> str | None:
    save_path = _extract_labeled_value(body, "Save exports as")
    return _reformat_placeholders(save_path) if save_path else None


def _clean_title(title: str) -> str:
    cleaned = title.strip().replace("“", '"').replace("”", '"').replace("`", "")
    return cleaned.replace('"', "").strip()


def _slug_title_source(title: str) -> str:
    without_issue = title.split(" — established during issue ", maxsplit=1)[0]
    return re.sub(r"\s+\([^)]*\)$", "", without_issue).strip()


def _reformat_placeholders(text: str) -> str:
    return PLACEHOLDER_RE.sub(lambda match: "{{" + _placeholder_name(match.group(1)) + "}}", text)


def _placeholder_name(raw_name: str) -> str:
    lowered = raw_name.strip().replace("×", "x").replace("/", " ")
    lowered = re.sub(r"[^A-Za-z0-9]+", "_", lowered)
    return re.sub(r"_+", "_", lowered).strip("_").lower()


def _service_tool_label(tql: str, tool: str | None) -> str:
    services = sorted(set(SERVICE_RE.findall(tql)))
    service_label = services[0] if len(services) == 1 else "multi-service"
    if services and tool:
        return f"{service_label} / {tool}"
    if services:
        return service_label
    if tool and "spans " in tql:
        return f"multi-service / {tool}"
    return tool or "—"


def _normalize_inline_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_wrapping_ticks(text: str) -> str:
    stripped = text.strip()
    return stripped[1:-1] if stripped.startswith("`") and stripped.endswith("`") else stripped


def _render_template_file(entry: CatalogEntry) -> str:
    lines = [
        f"# {entry.title}",
        "",
        *_render_bullet("Purpose", entry.purpose or "—"),
        *_render_bullet("Tool", f"`{entry.tool}`" if entry.tool else "—"),
        *_render_bullet("Save exports as", f"`{entry.save_exports_as}`" if entry.save_exports_as else "—"),
        *_render_bullet("Source file", f"`{entry.source}`"),
        *_render_bullet("Source section", f"`{entry.title}`"),
        "",
        "```",
        entry.tql,
        "```",
        "",
    ]
    return "\n".join(lines)


def _render_index(catalog: list[CatalogEntry]) -> str:
    rows = [_render_index_row(entry) for entry in catalog] or ["| — | — | — | — |"]
    source_path = catalog[0].source if catalog else DEFAULT_SOURCE
    lines = [
        "# Lightstep query catalog",
        "",
        "Generated by `scripts/dev/harvest_lightstep_query_catalog.py` from the read-only Lightstep template source.",
        "",
        f"Source file: `{source_path}`",
        "",
        "| Slug | Service/tool | Purpose | Source |",
        "|---|---|---|---|",
        *rows,
        "",
    ]
    return "\n".join(lines)


def _render_index_row(entry: CatalogEntry) -> str:
    source = _escape_table(_index_source(entry.title))
    return (
        f"| `{_escape_table(entry.slug)}` | {_escape_table(entry.service_tool)} | "
        f"{_escape_table(_index_purpose(entry.purpose))} | {source} |"
    )


def _escape_table(text: str) -> str:
    return text.replace("|", r"\|")


def _render_bullet(label: str, value: str) -> list[str]:
    wrapped = textwrap.fill(
        value,
        width=200,
        initial_indent=f"- {label}: ",
        subsequent_indent="  ",
    )
    return wrapped.splitlines()


def _index_purpose(purpose: str | None) -> str:
    if not purpose:
        return "—"
    compact = _normalize_inline_whitespace(purpose)
    if len(compact) <= 80:
        return compact
    shortened = compact[:77].rsplit(" ", maxsplit=1)[0].rstrip(",.;:")
    return f"{shortened}…"


def _index_source(title: str) -> str:
    compact = _slug_title_source(title).split(" — ", maxsplit=1)[0].strip()
    return compact


if __name__ == "__main__":
    main()
