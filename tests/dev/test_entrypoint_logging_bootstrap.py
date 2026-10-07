"""Smoke tests for entry-point logging bootstrap coverage."""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.athena import discover_athena_tables, run_table_ddl_export
from scripts.dev import reflow_md, update_athena_table_ddl_knowledge
from scripts.reference_diagram import main as reference_diagram_main
import scripts.resolve_tenant as resolve_tenant


def test_discover_athena_tables_apply_log_level_accepts_lowercase() -> None:
    original_level = logging.getLogger().level
    try:
        discover_athena_tables._apply_log_level("debug")
        assert logging.getLogger().getEffectiveLevel() == logging.DEBUG
    finally:
        logging.getLogger().setLevel(original_level)


def test_run_table_ddl_export_apply_log_level_accepts_lowercase() -> None:
    original_level = logging.getLogger().level
    try:
        run_table_ddl_export._apply_log_level("warning")
        assert logging.getLogger().getEffectiveLevel() == logging.WARNING
    finally:
        logging.getLogger().setLevel(original_level)


def test_discover_athena_tables_main_calls_init_logging(monkeypatch, tmp_path) -> None:
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
            force=False,
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

    result = discover_athena_tables.main([])

    assert result == 0
    init_logging.assert_called_once_with("discover-athena-tables")


def test_run_table_ddl_export_main_calls_init_logging(monkeypatch) -> None:
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
            force=False,
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

    result = run_table_ddl_export.main([])

    assert result == 0
    init_logging.assert_called_once_with("run-table-ddl-export")


def test_reflow_md_main_calls_init_logging(monkeypatch, tmp_path) -> None:
    init_logging = Mock()
    markdown = tmp_path / "README.md"
    markdown.write_text("short line\n", encoding="utf-8")
    monkeypatch.setattr(reflow_md, "init_logging", init_logging)

    result = reflow_md.main([str(markdown)])

    assert result == 0
    init_logging.assert_called_once_with("reflow-md")


def test_update_athena_table_ddl_knowledge_main_calls_init_logging(monkeypatch, tmp_path) -> None:
    init_logging = Mock()
    csv_path = tmp_path / "ddl.csv"
    markdown_path = tmp_path / "knowledge.md"
    csv_path.write_text("table_name,ddl\nfoo,SELECT 1\n", encoding="utf-8")
    markdown_path.write_text("# Knowledge\n", encoding="utf-8")
    monkeypatch.setattr(update_athena_table_ddl_knowledge, "init_logging", init_logging)

    result = update_athena_table_ddl_knowledge.main(["--csv", str(csv_path), "--markdown", str(markdown_path)])

    assert result == 0
    init_logging.assert_called_once_with("update-athena-table-ddl-knowledge")


def test_reference_diagram_main_calls_init_logging(monkeypatch, tmp_path) -> None:
    init_logging = Mock()
    source = tmp_path / "source"
    out_path = tmp_path / "docs" / "reference.md"
    source.mkdir()
    monkeypatch.setattr(reference_diagram_main, "init_logging", init_logging)
    monkeypatch.setattr(reference_diagram_main, "discover_projects", lambda path: {})
    monkeypatch.setattr(reference_diagram_main, "link_cross_project_imports", lambda projects: None)
    monkeypatch.setattr(reference_diagram_main, "render_report", lambda projects, root: "# report\n")
    monkeypatch.setattr(
        reference_diagram_main.sys,
        "argv",
        ["main.py", "--source", str(source), "--out", str(out_path)],
    )

    reference_diagram_main.main()

    assert out_path.read_text(encoding="utf-8") == "# report\n"
    init_logging.assert_called_once_with("reference-diagram")


def test_resolve_tenant_main_calls_init_logging(monkeypatch) -> None:
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

    result = resolve_tenant.main(["--system", "lightstep_go", "--tenant", "GH"])

    assert result == 0
    init_logging.assert_called_once_with("resolve-tenant")
