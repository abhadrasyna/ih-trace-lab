"""Smoke tests covering init_logging bootstrap on remaining script entry points."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.athena import discover_athena_tables, run_table_ddl_export
from scripts.dev import (
    archive_completed_story,
    check_project_taxonomy,
    generate_code_registry,
    generate_scripts_registry,
    harvest_athena_query_catalog,
    harvest_lightstep_query_catalog,
    monitor_worktree_progress,
    promote_scratch_scripts,
    reflow_md,
    update_athena_table_ddl_knowledge,
)
from scripts.reference_diagram import main as reference_diagram_main
import scripts.resolve_tenant as resolve_tenant


def test_archive_completed_story_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    monkeypatch.setattr(archive_completed_story, "init_logging", init_logging)
    monkeypatch.setattr(archive_completed_story, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(archive_completed_story, "archive", lambda root, slug: [root / "docs" / slug / "tasks.md"])
    monkeypatch.setattr(archive_completed_story, "_dangling_references", lambda root, slug: [])

    assert archive_completed_story.main(["demo-story"]) == 0
    init_logging.assert_called_once_with("archive-completed-story")


def test_check_project_taxonomy_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    monkeypatch.setattr(check_project_taxonomy, "init_logging", init_logging)
    monkeypatch.setattr(sys, "argv", ["check_project_taxonomy.py", "--root", str(tmp_path)])

    check_project_taxonomy.main()
    init_logging.assert_called_once_with("check-project-taxonomy")


def test_generate_code_registry_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    out_path = tmp_path / "CODE_REGISTRY.md"
    monkeypatch.setattr(generate_code_registry, "init_logging", init_logging)
    monkeypatch.setattr(sys, "argv", ["generate_code_registry.py", "--root", str(tmp_path), "--out", str(out_path)])

    generate_code_registry.main()
    init_logging.assert_called_once_with("generate-code-registry")


def test_generate_scripts_registry_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    out_path = tmp_path / "SCRIPTS.md"
    monkeypatch.setattr(generate_scripts_registry, "init_logging", init_logging)
    monkeypatch.setattr(sys, "argv", ["generate_scripts_registry.py", "--root", str(tmp_path), "--out", str(out_path)])

    generate_scripts_registry.main()
    init_logging.assert_called_once_with("generate-scripts-registry")


def test_harvest_athena_query_catalog_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    monkeypatch.setattr(harvest_athena_query_catalog, "init_logging", init_logging)
    monkeypatch.setattr(harvest_athena_query_catalog, "build_catalog", lambda paths: [])
    monkeypatch.setattr(harvest_athena_query_catalog, "write_catalog", lambda root, catalog: None)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(harvest_athena_query_catalog.sys, "argv", ["harvest_athena_query_catalog.py"])

    harvest_athena_query_catalog.main()
    init_logging.assert_called_once_with("harvest-athena-query-catalog")


def test_harvest_lightstep_query_catalog_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    source = tmp_path / "templates.md"
    source.write_text("# T\n\n## Example\n\n```\nmetric requests\n```\n", encoding="utf-8")
    monkeypatch.setattr(harvest_lightstep_query_catalog, "init_logging", init_logging)
    monkeypatch.setattr(harvest_lightstep_query_catalog, "write_catalog", lambda root, catalog: None)
    monkeypatch.setattr(
        harvest_lightstep_query_catalog.sys,
        "argv",
        ["harvest_lightstep_query_catalog.py", "--source", str(source), "--root", str(tmp_path)],
    )

    harvest_lightstep_query_catalog.main()
    init_logging.assert_called_once_with("harvest-lightstep-query-catalog", to_file=False)


def test_monitor_worktree_progress_calls_init_logging(monkeypatch) -> None:
    init_logging = Mock()
    monkeypatch.setattr(monitor_worktree_progress, "init_logging", init_logging)
    monkeypatch.setattr(monitor_worktree_progress, "validate_story_names", lambda stories, plan_root: [])
    monkeypatch.setattr(monitor_worktree_progress, "check_story", lambda story, worktree_root, plan_root: None)
    monkeypatch.setattr(monitor_worktree_progress, "describe_missing_worktree", lambda story, plan_root: "not started yet")
    monkeypatch.setattr(sys, "argv", ["monitor_worktree_progress.py", "--story", "demo-story"])

    assert monitor_worktree_progress.main() == 0
    init_logging.assert_called_once_with("monitor-worktree-progress")


def test_promote_scratch_scripts_calls_init_logging(monkeypatch) -> None:
    init_logging = Mock()
    monkeypatch.setattr(promote_scratch_scripts, "init_logging", init_logging)
    monkeypatch.setattr(promote_scratch_scripts, "find_promotion_candidates", lambda scratch_dir, days: [])
    monkeypatch.setattr(sys, "argv", ["promote_scratch_scripts.py", "--list"])

    promote_scratch_scripts.main()
    init_logging.assert_called_once_with("promote-scratch-scripts")


def test_reflow_md_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    markdown = tmp_path / "README.md"
    markdown.write_text("short line\n", encoding="utf-8")
    monkeypatch.setattr(reflow_md, "init_logging", init_logging)

    assert reflow_md.main([str(markdown)]) == 0
    init_logging.assert_called_once_with("reflow-md")


def test_update_athena_table_ddl_knowledge_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    csv_path = tmp_path / "ddl.csv"
    markdown_path = tmp_path / "knowledge.md"
    csv_path.write_text("table_name,ddl\nfoo,SELECT 1\n", encoding="utf-8")
    markdown_path.write_text("# Knowledge\n", encoding="utf-8")
    monkeypatch.setattr(update_athena_table_ddl_knowledge, "init_logging", init_logging)

    assert update_athena_table_ddl_knowledge.main(["--csv", str(csv_path), "--markdown", str(markdown_path)]) == 0
    init_logging.assert_called_once_with("update-athena-table-ddl-knowledge")


def test_discover_athena_tables_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    monkeypatch.setattr(discover_athena_tables, "init_logging", init_logging)
    monkeypatch.setattr(
        discover_athena_tables,
        "_parse_args",
        lambda argv=None: SimpleNamespace(
            database="analytics",
            profile="profile",
            workgroup="wg",
            output_location="s3://bucket/out",
            output_dir=str(tmp_path),
            region=None,
            output=None,
            skip_auth_check=True,
            log_level="INFO",
        ),
    )
    monkeypatch.setattr(
        discover_athena_tables,
        "_load_athena_dependencies",
        lambda: SimpleNamespace(
            config_lib=SimpleNamespace(RunConfig=lambda **kwargs: kwargs),
            athena_cli_common=SimpleNamespace(build_executor=lambda run_config: ("executor", "downloader")),
        ),
    )
    monkeypatch.setattr(discover_athena_tables, "discover_tables", lambda executor, downloader, database: ["table_a"])

    assert discover_athena_tables.main([]) == 0
    init_logging.assert_called_once_with("discover-athena-tables")


def test_run_table_ddl_export_calls_init_logging(monkeypatch) -> None:
    init_logging = Mock()
    monkeypatch.setattr(run_table_ddl_export, "init_logging", init_logging)
    monkeypatch.setattr(
        run_table_ddl_export,
        "_parse_args",
        lambda argv=None: SimpleNamespace(
            database="analytics",
            profile="profile",
            workgroup="wg",
            output_location="s3://bucket/out",
            output_dir="output",
            region=None,
            poll_interval=2,
            timeout=300,
            tables="table_a",
            tables_csv=None,
            batch_size=10,
            output=None,
            dry_run=True,
            skip_auth_check=True,
            log_level="INFO",
        ),
    )
    monkeypatch.setattr(
        run_table_ddl_export,
        "_load_athena_dependencies",
        lambda: SimpleNamespace(
            config_lib=SimpleNamespace(RunConfig=lambda **kwargs: kwargs),
            athena_cli_common=SimpleNamespace(),
            exceptions=SimpleNamespace(SsoLoginError=RuntimeError),
        ),
    )

    assert run_table_ddl_export.main([]) == 0
    init_logging.assert_called_once_with("run-table-ddl-export")


def test_reference_diagram_calls_init_logging(monkeypatch, tmp_path: Path) -> None:
    init_logging = Mock()
    source = tmp_path / "source"
    out_path = tmp_path / "docs" / "reference.md"
    source.mkdir()
    monkeypatch.setattr(reference_diagram_main, "init_logging", init_logging)
    monkeypatch.setattr(reference_diagram_main, "discover_projects", lambda path: {})
    monkeypatch.setattr(reference_diagram_main, "link_cross_project_imports", lambda projects: None)
    monkeypatch.setattr(reference_diagram_main, "render_report", lambda projects, root: "# report\n")
    monkeypatch.setattr(reference_diagram_main.sys, "argv", ["main.py", "--source", str(source), "--out", str(out_path)])

    reference_diagram_main.main()
    init_logging.assert_called_once_with("reference-diagram")


def test_resolve_tenant_calls_init_logging(monkeypatch) -> None:
    init_logging = Mock()
    monkeypatch.setattr(resolve_tenant, "init_logging", init_logging)
    monkeypatch.setattr(resolve_tenant, "TenantRegistry", lambda: SimpleNamespace(get=lambda tenant: {"tenant": tenant}))
    monkeypatch.setattr(
        resolve_tenant,
        "LightstepGoQueryTarget",
        lambda: SimpleNamespace(build_context=lambda tenant: {"resolved": tenant["tenant"]}),
    )
    monkeypatch.setattr(resolve_tenant, "MatisseQueryTarget", lambda: SimpleNamespace(build_context=lambda tenant: {}))
    monkeypatch.setattr(resolve_tenant, "AthenaQueryTarget", lambda: SimpleNamespace(build_context=lambda tenant: {}))

    assert resolve_tenant.main(["--system", "lightstep_go", "--tenant", "GH"]) == 0
    init_logging.assert_called_once_with("resolve-tenant")
