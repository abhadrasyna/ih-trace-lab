"""Strategy implementers for `functional-code-taxonomy` FCT-2's `ReportRenderer` Protocol.

Design notes (see `docs/plan/src-lib-migration/report-render-lib-migration/stories.md` RRM-2 for the full spec this implements):

`PYTHON_DESIGN.md` trigger: OCP — the audited originals (`github_copilot/vod-playback-timing-probe`, `mtn-zm-session-device-investigation`, `ctap-smvod-session-report`) each hand-rolled their own
markdown/summary formatting as a copy-pasted `to_csv`/print-loop; a new report shape meant copying one of those scripts rather than reusing anything. Here, each shape is its own `ReportRenderer`
implementer; a new shape in the future is a new class, never an edit to an existing one.

Each implementer's `render(rows)` returns a fully-formatted string and performs no file I/O of its own — rendering (this module) is deliberately split from writing (the caller's own choice, or
`csv_io`), matching FCT-2's own design. Row shape is intentionally loose (`list[dict[str, str]]` per the Protocol) since no project-specific schema is fixed here; each writer documents the row keys
it looks for and degrades gracefully (empty section, not a crash) when an expected key is absent from every row.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

_DEFAULT_TOP_N = 5


def _escape_markdown_cell(value: object) -> str:
    """Escapes backslashes and `|`, and collapses newlines, so a cell value can't shift/split a markdown table's columns.

    Backslashes are escaped first — otherwise a value already containing `\\|` would become `\\\\|`, which GitHub-flavored markdown reads as an escaped backslash followed by an unescaped `|`,
    still splitting the cell.
    """
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


class MarkdownTableWriter:
    """Shape 1 — a flat markdown table, one row per event/item.

    Ports `vod-playback-timing-probe`'s `generate_timing_report.py` / `har_probe_comparison_report.py` shape: an ordered set of columns, one table row per input row.
    """

    def render(self, rows: list[dict[str, str]]) -> str:
        if not rows:
            return "_No rows to report._\n"
        columns = self._ordered_columns(rows)
        header = "| " + " | ".join(_escape_markdown_cell(column) for column in columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"
        body_lines = [self._format_row(row, columns) for row in rows]
        return "\n".join([header, separator, *body_lines]) + "\n"

    @staticmethod
    def _ordered_columns(rows: list[dict[str, str]]) -> list[str]:
        """Union of every row's keys, in first-seen order — a key that only appears in a later row is still a column, never silently dropped."""
        columns: dict[str, None] = {}
        for row in rows:
            for key in row:
                columns.setdefault(key, None)
        return list(columns)

    @staticmethod
    def _format_row(row: dict[str, str], columns: list[str]) -> str:
        return "| " + " | ".join(_escape_markdown_cell(row.get(column, "")) for column in columns) + " |"


class CategoryBreakdownWriter:
    """Shape 2 — counts by category, plus a most-common top-N section.

    Ports `mtn-zm-session-device-investigation`'s `generate_summary.py` / `summarize_final_session_report.py` shape. Looks for a `"category"` key on each row; rows missing it are grouped under
    `"(uncategorized)"` rather than dropped or raising, since a partially-tagged dataset is still worth summarizing.
    """

    def __init__(self, top_n: int = _DEFAULT_TOP_N) -> None:
        if top_n < 0:
            raise ValueError(f"top_n must be >= 0, got {top_n!r}")
        self._top_n = top_n

    def render(self, rows: list[dict[str, str]]) -> str:
        counts = Counter(row.get("category") or "(uncategorized)" for row in rows)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        shown_n = min(self._top_n, len(ranked))
        lines = ["## Category Breakdown", ""]
        lines.extend(self._counts_table(ranked))
        lines.append("")
        lines.append(f"### Top {shown_n}")
        lines.append("")
        lines.extend(self._top_n_lines(ranked))
        return "\n".join(lines) + "\n"

    @staticmethod
    def _counts_table(ranked: list[tuple[str, int]]) -> list[str]:
        lines = ["| Category | Count |", "| --- | --- |"]
        for category, count in ranked:
            lines.append(f"| {_escape_markdown_cell(category)} | {count} |")
        return lines

    def _top_n_lines(self, ranked: list[tuple[str, int]]) -> list[str]:
        return [
            f"{rank}. {_escape_markdown_cell(category)} ({count})"
            for rank, (category, count) in enumerate(ranked[: self._top_n], start=1)
        ]


class StatisticalWriteupWriter:
    """Shape 3 — a richer multi-section write-up: distribution, buffering/startup stats, outliers, breakdown, and an anomaly scan.

    Ports `ctap-smvod-session-report`'s `analyze_outcome_report.py` shape. Looks for an optional numeric `"value"` key (for distribution/outlier stats), optional numeric `"buffering_ms"` /
    `"startup_ms"` keys, an optional `"category"` key (reuses `CategoryBreakdownWriter`'s counting for the breakdown section), and an optional truthy `"anomaly"` key. A section whose keys are
    absent from every row degrades gracefully rather than raising — distribution/buffering/outliers/anomaly-scan render "no data"/"None detected"; the breakdown section instead shows every row
    grouped under `"(uncategorized)"`, matching `CategoryBreakdownWriter`'s own fallback, since no single original script covers every section's input shape.
    """

    _OUTLIER_IQR_MULTIPLIER = 1.5
    _OUTLIER_MIN_SAMPLE_SIZE = 4

    def render(self, rows: list[dict[str, str]]) -> str:
        sections = [
            self._distribution_section(rows),
            self._buffering_startup_section(rows),
            self._outliers_section(rows),
            self._breakdown_section(rows),
            self._anomaly_scan_section(rows),
        ]
        return "\n".join(sections) + "\n"

    def _distribution_section(self, rows: list[dict[str, str]]) -> str:
        values = self._numeric_values(rows, "value")
        if not values:
            return "## Distribution\n\nNo numeric `value` data.\n"
        lines = [
            "## Distribution",
            "",
            f"- count: {len(values)}",
            f"- mean: {statistics.mean(values):.2f}",
            f"- median: {statistics.median(values):.2f}",
            f"- min: {min(values):.2f}",
            f"- max: {max(values):.2f}",
        ]
        return "\n".join(lines) + "\n"

    def _buffering_startup_section(self, rows: list[dict[str, str]]) -> str:
        lines = ["## Buffering / Startup Stats", ""]
        for label, key in (("Buffering (ms)", "buffering_ms"), ("Startup (ms)", "startup_ms")):
            values = self._numeric_values(rows, key)
            if values:
                lines.append(f"- {label}: mean {statistics.mean(values):.2f}, min {min(values):.2f}, max {max(values):.2f}")
            else:
                lines.append(f"- {label}: no data")
        return "\n".join(lines) + "\n"

    def _outliers_section(self, rows: list[dict[str, str]]) -> str:
        values = self._numeric_values(rows, "value")
        if len(values) < self._OUTLIER_MIN_SAMPLE_SIZE:
            return "## Outliers\n\nNot enough `value` data to detect outliers.\n"
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
        iqr = q3 - q1
        lower_fence = q1 - self._OUTLIER_IQR_MULTIPLIER * iqr
        upper_fence = q3 + self._OUTLIER_IQR_MULTIPLIER * iqr
        outliers = [
            row
            for row in rows
            if (value := self._as_float(row.get("value"))) is not None and (value > upper_fence or value < lower_fence)
        ]
        if not outliers:
            return "## Outliers\n\nNone detected.\n"
        lines = [
            "## Outliers",
            "",
            f"{len(outliers)} row(s) outside [{lower_fence:.2f}, {upper_fence:.2f}] (Q1/Q3 \u00b1 {self._OUTLIER_IQR_MULTIPLIER:g}\u00d7IQR, Tukey's fence):",
            "",
        ]
        lines.extend(self._format_row_as_list_item(row) for row in outliers)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _breakdown_section(rows: list[dict[str, str]]) -> str:
        breakdown = CategoryBreakdownWriter().render(rows)
        return breakdown.replace("## Category Breakdown", "## Breakdown", 1)

    @staticmethod
    def _anomaly_scan_section(rows: list[dict[str, str]]) -> str:
        anomalies = [row for row in rows if str(row.get("anomaly", "")).strip().lower() in {"1", "true", "yes"}]
        if not anomalies:
            return "## Anomaly Scan\n\nNone detected.\n"
        lines = ["## Anomaly Scan", "", f"{len(anomalies)} row(s) flagged:", ""]
        lines.extend(StatisticalWriteupWriter._format_row_as_list_item(row) for row in anomalies)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_row_as_list_item(row: dict[str, str]) -> str:
        """Renders a row as a single escaped markdown list item — raw `dict` text would let an embedded `|`/newline break the list."""
        pairs = ", ".join(f"{key}={value}" for key, value in row.items())
        return f"- {_escape_markdown_cell(pairs)}"

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if math.isfinite(parsed) else None

    def _numeric_values(self, rows: list[dict[str, str]], key: str) -> list[float]:
        values = (self._as_float(row.get(key)) for row in rows)
        return [value for value in values if value is not None]
