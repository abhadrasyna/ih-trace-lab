"""Checks for the hand-exported Lightstep CSVs: presence, numbered parts, schema, tenant and UTC coverage.

Everything is driven by the registries below. To cover a new artifact, add it to ``CORE_COLUMNS`` (or to
``lib.drm_exports.REQUIRED_COLUMNS`` for mDRM) and, if it has timestamps, to ``TIME_COLUMNS``; presence, part
numbering, schema and tenant checks then apply with no further code.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.drm_exports import FAIRPLAY, LRM, MDRMFE, PLAYREADY, REQUIRED_COLUMNS, WIDEVINE
from lib.tenant_context import TenantContext, enforce_disambiguation

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
SIDECAR_SUFFIX = ".combined-from.json"
TENANT_ALIASES = ("busUnitId",)

CORE_COLUMNS: dict[str, tuple[str, ...]] = {
    "ctap": ("lightstep.trace_id", "http.user_agent"),
    "smvod": ("householdId", "deviceId", "sessionId", "lightstep.trace_id"),
    "smvod-ts": ("sessionId", "oldest_micros", "youngest_micros"),
}
CORE_KINDS = tuple(CORE_COLUMNS)
DRM_KINDS = (MDRMFE, LRM, WIDEVINE, PLAYREADY, FAIRPLAY)
REQUIRED_DRM_KINDS = (MDRMFE, LRM)  # the funnel's required inputs (run_pipeline._drm_exports_present)
ARTIFACT_COLUMNS = {**CORE_COLUMNS, **REQUIRED_COLUMNS}
# kind -> (first, last) timestamp columns, in microseconds since the epoch
TIME_COLUMNS: dict[str, tuple[str, str]] = {"smvod-ts": ("oldest_micros", "youngest_micros")}


@dataclass(frozen=True)
class Finding:
    level: str
    check: str
    detail: str
    subject: str = ""


@dataclass(frozen=True)
class Settings:
    tolerance: timedelta = timedelta(minutes=15)
    max_gap: timedelta = timedelta(minutes=15)
    row_cap: int = 500
    include_drm: bool = False


@dataclass(frozen=True)
class ArtifactFiles:
    kind: str
    whole: Path | None
    parts: dict[int, Path]

    @property
    def present(self) -> bool:
        return self.whole is not None or bool(self.parts)

    @property
    def effective(self) -> list[Path]:
        """Files holding the day's content: the whole-day file, else the parts in order."""
        return [self.whole] if self.whole else [self.parts[n] for n in sorted(self.parts)]

    @property
    def coverage_files(self) -> list[tuple[str, Path]]:
        """Per-part files when split (so gaps between parts are visible), else the whole-day file."""
        if self.parts:
            return [(f"part {n:02d}", self.parts[n]) for n in sorted(self.parts)]
        return [("whole-day", self.whole)] if self.whole else []


@dataclass(frozen=True)
class Span:
    first_us: int
    last_us: int
    count: int


def find_artifact_files(directory: Path, date_iso: str, kind: str) -> ArtifactFiles:
    whole = directory / f"{date_iso}_{kind}.csv"
    pattern = re.compile(rf"{re.escape(date_iso)}_(\d+)_{re.escape(kind)}\.csv")
    parts: dict[int, Path] = {}
    for path in directory.glob(f"{date_iso}_[0-9]*_{kind}.csv"):
        match = pattern.fullmatch(path.name)
        if match:
            parts[int(match.group(1))] = path
    return ArtifactFiles(kind, whole if whole.exists() else None, parts)


def check_presence(af: ArtifactFiles, required: bool) -> list[Finding]:
    if not af.present:
        if required:
            return [Finding(FAIL, "presence", "no whole-day file and no numbered parts", af.kind)]
        return []
    what = f"{len(af.parts)} part(s)" if af.parts else "whole-day file"
    return [Finding(PASS, "presence", what, af.kind)]


def check_part_numbers(af: ArtifactFiles) -> list[Finding]:
    if not af.parts:
        return []
    top = max(af.parts)
    missing = [n for n in range(1, top + 1) if n not in af.parts]
    if missing:
        names = ", ".join(f"{n:02d}" for n in missing)
        # mDRM exports are per-type windows; an empty type is skipped, so a numbering gap is only a warning there
        level = FAIL if af.kind in CORE_KINDS else WARN
        return [Finding(level, "parts", f"missing part(s) {names} (have {_nums(af.parts)})", af.kind)]
    return [Finding(PASS, "parts", f"01..{top:02d} contiguous", af.kind)]


def check_part_sets(files: dict[str, ArtifactFiles]) -> list[Finding]:
    """Core artifacts are exported together, so they must have the same part numbers."""
    core = {k: set(files[k].parts) for k in CORE_KINDS if k in files and files[k].parts}
    if not core:
        return []
    union = set().union(*core.values())
    findings = []
    for kind in CORE_KINDS:
        af = files.get(kind)
        if af is None or not af.parts:
            continue
        missing = sorted(union - set(af.parts))
        if missing:
            names = ", ".join(f"{n:02d}" for n in missing)
            findings.append(Finding(FAIL, "part-set", f"no part(s) {names}, which other core artifacts have", kind))
    return findings


def check_sidecar(af: ArtifactFiles) -> list[Finding]:
    """A whole-day file combined by Step 1b records the parts it was built from."""
    if af.whole is None:
        return []
    sidecar = af.whole.with_name(af.whole.name + SIDECAR_SUFFIX)
    if not sidecar.exists():
        return []
    listed = set(json.loads(sidecar.read_text(encoding="utf-8"))["parts"])
    on_disk = {p.name for p in af.parts.values()}
    deleted, added = sorted(listed - on_disk), sorted(on_disk - listed)
    findings = []
    if deleted:
        findings.append(Finding(FAIL, "combined-from", f"combined file was built from part(s) no longer on disk: {deleted}", af.kind))
    if added:
        findings.append(Finding(WARN, "combined-from", f"part(s) not in the combined file yet (Step 1b re-combines): {added}", af.kind))
    return findings


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def check_content(path: Path, kind: str, columns: list[str], rows: list[dict[str, str]]) -> list[Finding]:
    missing = [c for c in ARTIFACT_COLUMNS[kind] if c not in columns]
    findings = []
    if missing:
        findings.append(Finding(FAIL, "schema", f"{path.name}: missing column(s) {missing}", kind))
    if not rows:
        # an empty core export means a broken export; an empty mDRM/Release export is normal for a small tenant
        level = FAIL if kind in CORE_KINDS else WARN
        findings.append(Finding(level, "rows", f"{path.name}: header only, no data rows", kind))
    if not findings:
        findings.append(Finding(PASS, "schema", f"{path.name}: {len(rows)} row(s)", kind))
    return findings


def check_tenant(rows: list[dict[str, str]], context: TenantContext, path: Path, kind: str) -> Finding:
    try:
        enforce_disambiguation(rows, context, path.name, aliases=TENANT_ALIASES)
    except ValueError as exc:
        return Finding(FAIL, "tenant", str(exc), kind)
    return Finding(PASS, "tenant", f"{path.name}: rows belong to {context.code}", kind)


def span_of(rows: list[dict[str, str]], first_col: str, last_col: str, source: str) -> Span:
    firsts, lasts = [], []
    for number, row in enumerate(rows, start=2):
        try:
            if row[first_col] and row[last_col]:
                firsts.append(int(row[first_col]))
                lasts.append(int(row[last_col]))
        except ValueError as exc:
            raise ValueError(f"{source} line {number}: non-numeric timestamp ({exc})") from exc
    if not firsts:
        raise ValueError(f"{source}: no row has {first_col}/{last_col} values")
    return Span(min(firsts), max(lasts), len(rows))


def _utc(us: int) -> datetime:
    return datetime.fromtimestamp(us / 1_000_000, timezone.utc)


def _hms(moment: datetime) -> str:
    return moment.strftime("%H:%M:%S")


def check_coverage(
    kind: str, spans: list[tuple[str, Span]], date_iso: str, settings: Settings, split: bool
) -> list[Finding]:
    """UTC day coverage. `spans` are in file order: edges, gaps between consecutive parts, and the row cap."""
    day_start = datetime.fromisoformat(date_iso).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    first = _utc(min(s.first_us for _, s in spans))
    last = _utc(max(s.last_us for _, s in spans))
    findings = []
    if first - day_start > settings.tolerance:
        findings.append(Finding(FAIL, "coverage", f"first span {_hms(first)} UTC is more than {_mins(settings.tolerance)} after 00:00", kind))
    if day_end - last > settings.tolerance:
        findings.append(Finding(FAIL, "coverage", f"last span {_hms(last)} UTC is more than {_mins(settings.tolerance)} before 24:00", kind))
    if first < day_start or last >= day_end:
        findings.append(Finding(WARN, "coverage", f"spans {_hms(first)}..{_hms(last)} reach outside {date_iso} UTC", kind))
    if split:
        findings += _check_part_gaps(kind, spans, settings)
    name, capped = spans[-1]
    if capped.count >= settings.row_cap:
        # The day edge check above already failed if the cut-off left a real hole at the end.
        findings.append(Finding(WARN, "row-cap", f"{name} has {capped.count} rows (cap {settings.row_cap}); rows after {_hms(_utc(capped.last_us))} UTC may be missing", kind))
    if not any(f.level == FAIL for f in findings):
        findings.append(Finding(PASS, "coverage", f"{_hms(first)}..{_hms(last)} UTC", kind))
    return findings


def _check_part_gaps(kind: str, spans: list[tuple[str, Span]], settings: Settings) -> list[Finding]:
    findings = []
    for (prev_name, prev), (name, cur) in zip(spans, spans[1:]):
        gap = timedelta(microseconds=cur.first_us - prev.last_us)
        if gap > settings.max_gap:
            findings.append(Finding(FAIL, "gap", f"{_hms(_utc(prev.last_us))}..{_hms(_utc(cur.first_us))} UTC uncovered between {prev_name} and {name}", kind))
        elif gap < timedelta(0):
            findings.append(Finding(WARN, "overlap", f"{prev_name} and {name} overlap by {-gap}", kind))
    return findings


def validate_tenant(
    directory: Path, date_iso: str, context: TenantContext, settings: Settings, drm_directory: Path | None = None
) -> list[Finding]:
    drm_dir = drm_directory or directory
    files = {k: find_artifact_files(directory, date_iso, k) for k in CORE_KINDS}
    files.update({k: find_artifact_files(drm_dir, date_iso, k) for k in DRM_KINDS})
    required = {*CORE_KINDS, *(REQUIRED_DRM_KINDS if settings.include_drm else ())}
    findings: list[Finding] = []
    for kind, af in files.items():
        findings += check_presence(af, kind in required)
        findings += check_part_numbers(af) + check_sidecar(af)
        findings += _check_files(af, context, date_iso, settings)
    return findings + check_part_sets(files)


def _check_files(af: ArtifactFiles, context: TenantContext, date_iso: str, settings: Settings) -> list[Finding]:
    findings: list[Finding] = []
    for path in af.effective if af.present else []:
        columns, rows = read_csv(path)
        content = check_content(path, af.kind, columns, rows)
        findings += content
        if af.kind in CORE_KINDS and rows and not any(f.level == FAIL for f in content):
            findings.append(check_tenant(rows, context, path, af.kind))
    if af.kind in TIME_COLUMNS and af.present:
        findings += _coverage_for(af, date_iso, settings)
    return findings


def _coverage_for(af: ArtifactFiles, date_iso: str, settings: Settings) -> list[Finding]:
    first_col, last_col = TIME_COLUMNS[af.kind]
    try:
        spans = [
            (name, span_of(read_csv(path)[1], first_col, last_col, path.name))
            for name, path in af.coverage_files
        ]
    except (ValueError, KeyError) as exc:
        return [Finding(FAIL, "coverage", f"cannot read timestamps: {exc}", af.kind)]
    return check_coverage(af.kind, spans, date_iso, settings, split=bool(af.parts))


def has_failures(findings: list[Finding]) -> bool:
    return any(f.level == FAIL for f in findings)


_COLUMNS = {
    "presence": "Presence", "parts": "Parts", "part-set": "Parts", "combined-from": "Parts",
    "schema": "Schema", "rows": "Schema", "tenant": "Tenant",
    "coverage": "Coverage", "gap": "Coverage", "overlap": "Coverage", "row-cap": "Coverage",
}
_HEADERS = ("Artifact", "Files", "Presence", "Parts", "Schema", "Tenant", "Coverage", "Result")
_SEVERITY = {PASS: 0, WARN: 1, FAIL: 2}


def _worst(levels: list[str]) -> str:
    return max(levels, key=_SEVERITY.__getitem__) if levels else "-"


_LEGEND = (
    ("Artifact", "Lightstep export type: ctap, smvod, smvod-ts (core, always required) and the mDRM exports."),
    ("Files", "What is on disk for the date: a whole-day file or N numbered _NN_ parts."),
    ("Presence", "FAIL if a required artifact has neither a whole-day file nor parts (mDRM required only with --drm)."),
    ("Parts", "Part numbers run 01..N with no gap (FAIL for core, WARN for mDRM); core artifacts have the same parts; "
              "a combined file's recorded parts still exist."),
    ("Schema", "Required columns are present and the file has data rows."),
    ("Tenant", "Rows belong to the tenant folder (shared Lightstep projects only); '-' for mDRM and dedicated projects."),
    ("Coverage", "smvod-ts only, the sole export with timestamps: first/last span within the tolerance of 00:00/24:00 UTC, "
                 "no gap between parts; WARN if the last part hit the row cap."),
    ("Result", "Worst level in the row. PASS ok, WARN review but does not block, FAIL blocks the pipeline; '-' not applicable."),
)


def format_legend() -> str:
    width = max(len(name) for name, _ in _LEGEND)
    return "\n".join(["Columns:", *(f"  {name.ljust(width)}  {text}" for name, text in _LEGEND)])


def format_report(tenant: str, findings: list[Finding]) -> str:
    """One table per tenant (artifact x check, worst level per cell), then the WARN/FAIL details."""
    kinds = list(dict.fromkeys(f.subject for f in findings))
    rows = []
    for kind in kinds:
        mine = [f for f in findings if f.subject == kind]
        cells = [_worst([f.level for f in mine if _COLUMNS[f.check] == column]) for column in _HEADERS[2:7]]
        files = next((f.detail for f in mine if f.check == "presence" and f.level == PASS), "-")
        rows.append([kind, files, *cells, _worst([f.level for f in mine])])
    table = [list(_HEADERS), *rows]
    widths = [max(len(str(r[i])) for r in table) for i in range(len(_HEADERS))]
    lines = [f"[{tenant}]"]
    for index, row in enumerate(table):
        lines.append("  " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)))
        if index == 0:
            lines.append("  " + "-+-".join("-" * w for w in widths))
    issues = [f for f in findings if f.level != PASS]
    lines += [f"  {f.level} {f.subject} ({f.check}): {f.detail}" for f in issues]
    return "\n".join(lines)


def _nums(parts: dict[int, Path]) -> str:
    return ", ".join(f"{n:02d}" for n in sorted(parts))


def _mins(delta: timedelta) -> str:
    return f"{int(delta.total_seconds() // 60)} min"
