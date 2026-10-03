"""Factory Method for selecting a `ReportRenderer` implementer by shape key.

See `docs/plan/src-lib-migration/report-render-lib-migration/stories.md` RRM-3 for the full spec this implements.

`PYTHON_DESIGN.md` trigger: Factory Method — RRM-2 defined one Strategy implementer per report shape but left the
"which implementer for this shape" decision to each call site, which would otherwise need its own
`if shape == "markdown_table": ...` chain — exactly the OCP violation RRM-2 was meant to close, just moved. This
module owns that decision in one place: adding a new shape is a one-line `REPORT_SHAPE_REGISTRY` entry, never an
edited branch at every call site.

Consumers should call `make_report_writer(shape)` and never import `MarkdownTableWriter` / `CategoryBreakdownWriter`
/ `StatisticalWriteupWriter` directly.
"""
from __future__ import annotations

from .protocols import ReportRenderer
from .writers import (
    CategoryBreakdownWriter,
    MarkdownTableWriter,
    StatisticalWriteupWriter,
)

REPORT_SHAPE_REGISTRY: dict[str, type[ReportRenderer]] = {
    "markdown_table": MarkdownTableWriter,
    "category_breakdown": CategoryBreakdownWriter,
    "statistical_writeup": StatisticalWriteupWriter,
}


def make_report_writer(shape: str) -> ReportRenderer:
    """Instantiates the `ReportRenderer` registered for `shape`.

    Raises `ValueError` (listing valid keys) for an unknown shape rather than silently falling back to a default.
    """
    try:
        writer_cls = REPORT_SHAPE_REGISTRY[shape]
    except KeyError:
        valid_keys = ", ".join(sorted(REPORT_SHAPE_REGISTRY))
        raise ValueError(f"Unknown report shape {shape!r}; valid keys are: {valid_keys}") from None
    return writer_cls()
