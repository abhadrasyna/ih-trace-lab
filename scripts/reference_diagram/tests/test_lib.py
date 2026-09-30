"""Tests for scripts/reference_diagram/lib.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reference_diagram.lib import (
    ProjectStats,
    build_internal_import_graph,
    discover_projects,
    extract_top_level_import_names,
    find_python_files,
    link_cross_project_imports,
    own_top_level_names,
    render_mermaid,
    render_project_flowchart,
    render_report,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --- find_python_files -------------------------------------------------------

def test_find_python_files_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "a.py")
    _write(tmp_path / "sub" / "b.py")
    found = find_python_files(tmp_path)
    assert {p.name for p in found} == {"a.py", "b.py"}


def test_find_python_files_prunes_excluded_dirs(tmp_path: Path) -> None:
    _write(tmp_path / ".venv" / "lib" / "site.py")
    _write(tmp_path / "real.py")
    found = find_python_files(tmp_path)
    assert [p.name for p in found] == ["real.py"]


# --- own_top_level_names ------------------------------------------------------

def test_own_top_level_names_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "main.py")
    (tmp_path / "scripts").mkdir()
    assert own_top_level_names(tmp_path) == {"main", "scripts"}


def test_own_top_level_names_ignores_excluded_and_hidden(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".git").mkdir()
    _write(tmp_path / "real.py")
    assert own_top_level_names(tmp_path) == {"real"}


# --- extract_top_level_import_names -------------------------------------------

def test_extract_top_level_import_names_happy_path(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    _write(f, "import os\nfrom collections import OrderedDict\nfrom . import sibling\n")
    names, used_fallback = extract_top_level_import_names(f)
    assert names == {"os", "collections"}  # relative import excluded
    assert used_fallback is False


def test_extract_top_level_import_names_falls_back_on_syntax_error(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    _write(f, "def broken(:\n    import shaka\n")
    names, used_fallback = extract_top_level_import_names(f)
    assert used_fallback is True
    assert "shaka" in names


# --- discover_projects ---------------------------------------------------------

def test_discover_projects_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "proj_a" / "run.py")
    _write(tmp_path / "proj_b" / "run.py")
    (tmp_path / "empty_dir").mkdir()
    _write(tmp_path / "not_a_project.txt")
    projects = discover_projects(tmp_path)
    assert set(projects) == {"proj_a", "proj_b"}
    assert projects["proj_a"].file_count == 1


def test_discover_projects_skips_hidden_and_excluded(tmp_path: Path) -> None:
    _write(tmp_path / ".git" / "hooks" / "pre-commit.py")
    _write(tmp_path / "real" / "run.py")
    projects = discover_projects(tmp_path)
    assert set(projects) == {"real"}


# --- link_cross_project_imports -------------------------------------------------

def test_link_cross_project_imports_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "foo" / "run.py", "import bar\n")
    _write(tmp_path / "bar" / "lib.py", "x = 1\n")
    projects = discover_projects(tmp_path)
    link_cross_project_imports(projects)
    assert projects["foo"].imported_projects == {"bar"}
    assert projects["bar"].imported_projects == set()


def test_link_cross_project_imports_ignores_own_package_and_generic_names(tmp_path: Path) -> None:
    # foo has its own "scripts" package (generic-name convention) and its own
    # nested "bar" package that happens to share a sibling project's name.
    _write(tmp_path / "foo" / "run.py", "import scripts\nimport bar\n")
    _write(tmp_path / "foo" / "scripts" / "__init__.py")
    _write(tmp_path / "foo" / "bar" / "__init__.py")
    _write(tmp_path / "bar" / "lib.py", "x = 1\n")
    projects = discover_projects(tmp_path)
    link_cross_project_imports(projects)
    # "scripts" is generic, "bar" resolves to foo's own local package -> no false edge.
    assert projects["foo"].imported_projects == set()


def test_link_cross_project_imports_skips_ambiguous_alias(tmp_path: Path) -> None:
    # "foo-x" and "foo_x" both normalize to the module alias "foo_x": ambiguous, skip.
    _write(tmp_path / "consumer" / "run.py", "import foo_x\n")
    _write(tmp_path / "foo-x" / "lib.py", "x = 1\n")
    _write(tmp_path / "foo_x" / "lib.py", "x = 1\n")
    projects = discover_projects(tmp_path)
    link_cross_project_imports(projects)
    assert projects["consumer"].imported_projects == set()


# --- build_internal_import_graph / render_project_flowchart --------------------

def test_build_internal_import_graph_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "pkg" / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "sample" / "pkg" / "runner.py", "from .helper import VALUE\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    runner = tmp_path / "sample" / "pkg" / "runner.py"
    helper = tmp_path / "sample" / "pkg" / "helper.py"
    assert graph[runner] == {helper}


def test_build_internal_import_graph_resolves_absolute_same_project_imports(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "pkg" / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "sample" / "pkg" / "runner.py", "from pkg.helper import VALUE\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    assert graph[tmp_path / "sample" / "pkg" / "runner.py"] == {tmp_path / "sample" / "pkg" / "helper.py"}


def test_build_internal_import_graph_no_edges_for_external_imports(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "runner.py", "import os\nfrom collections import defaultdict\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    assert graph[tmp_path / "sample" / "runner.py"] == set()


def test_build_internal_import_graph_supports_src_layout_imports(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "src" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "src" / "pkg" / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "sample" / "src" / "pkg" / "runner.py", "from pkg.helper import VALUE\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    assert graph[tmp_path / "sample" / "src" / "pkg" / "runner.py"] == {tmp_path / "sample" / "src" / "pkg" / "helper.py"}


def test_build_internal_import_graph_supports_sys_path_rooted_imports(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "scripts" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "scripts" / "pkg" / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "sample" / "scripts" / "pkg" / "runner.py", "from pkg.helper import VALUE\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    assert graph[tmp_path / "sample" / "scripts" / "pkg" / "runner.py"] == {
        tmp_path / "sample" / "scripts" / "pkg" / "helper.py"
    }


def test_build_internal_import_graph_drops_ambiguous_module_aliases(tmp_path: Path) -> None:
    _write(tmp_path / "sample" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "pkg" / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "sample" / "src" / "pkg" / "__init__.py")
    _write(tmp_path / "sample" / "src" / "pkg" / "helper.py", "VALUE = 2\n")
    _write(tmp_path / "sample" / "runner.py", "from pkg.helper import VALUE\n")
    project = discover_projects(tmp_path)["sample"]
    graph = build_internal_import_graph(project)
    assert graph[tmp_path / "sample" / "runner.py"] == set()


def test_render_project_flowchart_happy_path(tmp_path: Path) -> None:
    root = tmp_path / "sample"
    a = root / "runner.py"
    b = root / "helper.py"
    project = ProjectStats(name="sample", root_dir=root, py_files=[a, b])
    rendered = render_project_flowchart(project, {a: {b}, b: set()})
    assert rendered.startswith("```mermaid\nflowchart TD\n")
    assert 'runner.py"]' in rendered
    assert 'helper.py"]' in rendered
    assert "-->" in rendered


# --- render_mermaid / render_report --------------------------------------------

def _stats(name: str, root_dir: Path, count: int = 1) -> ProjectStats:
    return ProjectStats(name=name, root_dir=root_dir, py_files=[root_dir / "a.py"] * count)


def test_render_mermaid_happy_path(tmp_path: Path) -> None:
    projects = {"foo": _stats("foo", tmp_path / "foo", 3)}
    out = render_mermaid(projects)
    assert "```mermaid" in out
    assert "foo" in out
    assert "3 .py files" in out


def test_render_mermaid_escapes_reserved_and_quote_chars(tmp_path: Path) -> None:
    a = _stats("end", tmp_path / "end")
    b = _stats('weird"name', tmp_path / "weird")
    projects = {"end": a, 'weird"name': b}
    out = render_mermaid(projects)
    # "end" is a Mermaid keyword: its node id must not be the bare word "end".
    assert "\n    end[" not in out
    assert "&quot;" in out


def test_render_report_flags_fallback_files(tmp_path: Path) -> None:
    stats = _stats("foo", tmp_path / "foo")
    stats.unparsable_files.append(tmp_path / "foo" / "bad.py")
    report = render_report({"foo": stats}, tmp_path)
    assert "1 file(s) failed to parse" in report
    assert str(tmp_path) not in report  # only root.name, not the absolute path, is embedded
