"""Pure logic for scanning the github_copilot reference repo's Python files
and rendering a high-level Mermaid overview diagram.

No file I/O beyond the explicit functions below; callers (main()) own all
path resolution and writing.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXCLUDE_DIR_NAMES = frozenset({".venv", ".git", "__pycache__", ".obsidian", "node_modules"})

# Package/module names that recur, independently, across many otherwise-unrelated
# projects by convention (e.g. every project has its own scripts/ and logs/ folder).
# Treating a match against these as a cross-project import would produce false edges.
GENERIC_MODULE_NAMES = frozenset({"scripts", "logs", "lib", "tests", "tooling", "config", "src"})

# Mermaid keywords that break parsing if used verbatim as a node id.
_MERMAID_RESERVED_IDS = frozenset({"graph", "end", "subgraph", "class", "style", "click"})


@dataclass
class ProjectStats:
    """Python-file stats for one top-level folder of the reference repo."""

    name: str
    root_dir: Path
    py_files: list[Path] = field(default_factory=list)
    imported_projects: set[str] = field(default_factory=set)
    unparsable_files: list[Path] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.py_files)


def find_python_files(project_dir: Path, exclude_dir_names: frozenset[str] = DEFAULT_EXCLUDE_DIR_NAMES) -> list[Path]:
    """Recursively collect .py files under project_dir, pruning excluded dir names during the walk."""
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dir_names]
        for filename in filenames:
            if filename.endswith(".py"):
                result.append(Path(dirpath) / filename)
    return result


def own_top_level_names(project_dir: Path, exclude_dir_names: frozenset[str] = DEFAULT_EXCLUDE_DIR_NAMES) -> set[str]:
    """Top-level package (dir) and module (.py file) names a project defines directly under
    its own root — used to recognize "this project's own scripts/ package", not a sibling's."""
    names: set[str] = set()
    for entry in project_dir.iterdir():
        if entry.name in exclude_dir_names or entry.name.startswith("."):
            continue
        if entry.is_dir():
            names.add(entry.name)
        elif entry.suffix == ".py":
            names.add(entry.stem)
    return names


def discover_projects(
    root: Path,
    exclude_dir_names: frozenset[str] = DEFAULT_EXCLUDE_DIR_NAMES,
) -> dict[str, ProjectStats]:
    """Map each top-level, non-hidden, non-excluded subfolder of root to its ProjectStats."""
    projects: dict[str, ProjectStats] = {}
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name in exclude_dir_names:
            continue
        py_files = find_python_files(entry, exclude_dir_names)
        if py_files:
            projects[entry.name] = ProjectStats(name=entry.name, root_dir=entry, py_files=py_files)
    return projects


def extract_top_level_import_names(py_file: Path) -> tuple[set[str], bool]:
    """Return (top-level module/package names imported by py_file, used_fallback).

    used_fallback is True when the file failed to parse as Python and a regex-based
    heuristic scan was used instead (less accurate: may match strings/docstrings and
    only captures the first name in `import a, b`).
    """
    source = py_file.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, ValueError):
        return _regex_scan_imports(source), True

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import, stays within the same project
            if node.module:
                names.add(node.module.split(".")[0])
    return names, False


def _regex_scan_imports(source: str) -> set[str]:
    pattern = re.compile(r"^\s*(?:from|import)\s+([\w]+)", re.MULTILINE)
    return set(pattern.findall(source))


def link_cross_project_imports(projects: dict[str, ProjectStats]) -> None:
    """Mutate each ProjectStats.imported_projects with sibling project names it imports from.

    A project "imports" a sibling only if all of these hold for some import name X:
      - X matches the sibling folder's name (accounting for '-' -> '_' module-name normalization)
      - X is not one of GENERIC_MODULE_NAMES (scripts/logs/lib/... recur per-project by convention)
      - X is not also a top-level package/module the importing project defines itself
        (ruling out "this project's own scripts/ package" shadowing a sibling's name)
    Also records any files that needed the regex fallback, for reporting.
    """
    name_by_module_alias: dict[str, list[str]] = {}
    for name in projects:
        name_by_module_alias.setdefault(name.replace("-", "_"), []).append(name)

    for project in projects.values():
        own_names = own_top_level_names(project.root_dir)

        for py_file in project.py_files:
            imported, used_fallback = extract_top_level_import_names(py_file)
            if used_fallback:
                project.unparsable_files.append(py_file)
            for name in imported:
                if name in GENERIC_MODULE_NAMES or name in own_names:
                    continue
                targets = name_by_module_alias.get(name, [])
                # Skip ambiguous aliases (two sibling folders normalizing to the same name)
                # rather than silently picking one.
                if len(targets) == 1 and targets[0] != project.name:
                    project.imported_projects.add(targets[0])


def _mermaid_node_id(name: str, seen: dict[str, str]) -> str:
    """Return a Mermaid-safe, collision-free node id for name, reusing prior ids for repeats."""
    if name in seen:
        return seen[name]
    base = re.sub(r"[^0-9A-Za-z_]", "_", name) or "node"
    if base[0].isdigit():
        base = f"n_{base}"
    candidate = base
    suffix = 1
    existing_ids = set(seen.values())
    while candidate in existing_ids or candidate in _MERMAID_RESERVED_IDS:
        suffix += 1
        candidate = f"{base}_{suffix}"
    seen[name] = candidate
    return candidate


def _mermaid_label(text: str) -> str:
    """Escape characters that would break a quoted Mermaid node label."""
    return text.replace("\\", "\\\\").replace('"', "&quot;")


def _table_cell(text: str) -> str:
    """Escape characters that would break a markdown table cell."""
    return text.replace("|", "\\|")


def render_mermaid(projects: dict[str, ProjectStats]) -> str:
    """Render a high-level Mermaid graph: one node per project (with file count),
    one edge per detected cross-project import."""
    node_ids: dict[str, str] = {}
    lines = ["```mermaid", "graph LR"]
    for name, stats in sorted(projects.items()):
        node_id = _mermaid_node_id(name, node_ids)
        label = _mermaid_label(f"{name}<br/>({stats.file_count} .py files)")
        lines.append(f'    {node_id}["{label}"]')
    for name, stats in sorted(projects.items()):
        node_id = node_ids[name]
        for target in sorted(stats.imported_projects):
            target_id = node_ids.get(target)
            if target_id:
                lines.append(f"    {node_id} --> {target_id}")
    lines.append("```")
    return "\n".join(lines)


def render_report(projects: dict[str, ProjectStats], root: Path) -> str:
    """Render the full markdown report: title, Mermaid diagram, and a per-project file-count table.

    Only root.name (not the full absolute path) is embedded in the report, to avoid leaking
    the local filesystem layout into a committed doc.
    """
    total_files = sum(stats.file_count for stats in projects.values())
    total_fallback = sum(len(stats.unparsable_files) for stats in projects.values())
    lines = [
        "# Reference Repository Python Overview",
        "",
        f"Auto-generated by `scripts/reference_diagram/main.py` — do not edit by hand; re-run the "
        f"generator instead after `{root.name}` changes.",
        "",
        f"Scanned `{root.name}`: {len(projects)} top-level projects, {total_files} Python files "
        "(excluding `.venv`, `.git`, `__pycache__`, `.obsidian`, `node_modules`). Cross-project edges "
        f"exclude generic per-project package names ({', '.join(sorted(GENERIC_MODULE_NAMES))}).",
        "",
    ]
    if total_fallback:
        lines.append(
            f"⚠️ {total_fallback} file(s) failed to parse as Python and used a less-accurate regex "
            "import scan; their detected imports may be incomplete or spurious. See per-project counts below."
        )
        lines.append("")
    lines += [
        "## Project overview",
        "",
        render_mermaid(projects),
        "",
        "## File counts",
        "",
        "| Project | .py files | Imports (detected) | Unparsable (fallback) |",
        "|---|---|---|---|",
    ]
    for name, stats in sorted(projects.items()):
        imports = _table_cell(", ".join(sorted(stats.imported_projects))) or "—"
        fallback_count = len(stats.unparsable_files) or "—"
        lines.append(f"| `{_table_cell(name)}` | {stats.file_count} | {imports} | {fallback_count} |")
    lines.append("")
    return "\n".join(lines)
