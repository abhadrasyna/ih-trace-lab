"""POC: build a MkDocs Material site from generated Conviva metric reports."""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPIC = ROOT / "docs/plan/conviva-metrics-recreation"
MARKER = ".mkdocs-poc-output"
REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([A-Za-z]+)_(.+)-report\.md$")
IMG_RE = re.compile(r"\]\((?:\.\./)+output/[^)/]+/charts/([^)]+)\)")

MKDOCS_YML = """site_name: Conviva metrics recreation
docs_dir: docs
site_dir: site
theme:
  name: material
  palette:
    scheme: slate
  features: [navigation.sections, content.code.copy]
plugins: [search]
nav:
  - Home: index.md
{nav}
"""


def collect(epic: Path, tenant: str | None, date: str | None):
    for path in sorted(epic.glob("*/*-report.md")):
        m = REPORT_RE.match(path.name)
        if m and (not date or m[1] == date) and (not tenant or m[2] == tenant):
            yield path, m[1], m[2], m[3]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "scratch/tmp/mkdocs-poc")
    ap.add_argument("--tenant")
    ap.add_argument("--date")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    out = args.out_dir
    out = out.resolve()
    if out.exists():
        if ROOT == out or ROOT.is_relative_to(out):
            sys.exit(f"refusing to wipe {out}: it contains the repo")
        if any(out.iterdir()) and not (out / MARKER).exists():
            sys.exit(f"refusing to wipe {out}: not empty and not a previous POC output")
        shutil.rmtree(out)
    docs = out / "docs"
    docs.mkdir(parents=True)
    (out / MARKER).write_text("created by 2026-10-28_mkdocs-reports-site_poc.py\n")

    pages, rows = [], []
    for path, date, tenant, metric in collect(EPIC, args.tenant, args.date):
        raw = path.read_text()
        text = IMG_RE.sub(rf"](../charts/{tenant}/\1)", raw)
        (docs / "charts" / tenant).mkdir(parents=True, exist_ok=True)
        for png in IMG_RE.findall(raw):
            src = ROOT / "output" / tenant / "charts" / png
            if src.exists():
                shutil.copy(src, docs / "charts" / tenant / png)
            else:
                print(f"missing chart: {src}", file=sys.stderr)
        rel = Path(metric) / f"{date}_{tenant}.md"
        if (docs / rel).exists():
            sys.exit(f"duplicate report for {rel}: {path}")
        (docs / rel).parent.mkdir(exist_ok=True)
        (docs / rel).write_text(text)
        pages.append((metric, rel))
        rows.append(f"| {metric} | {tenant} | {date} | [report]({rel}) |")

    if not pages:
        sys.exit("no reports matched the --tenant/--date filters")
    (docs / "index.md").write_text(
        "# Conviva metrics\n\n| Metric | Tenant | Date | Link |\n|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )
    nav = "\n".join(f"  - '{m}': {r}" for m, r in pages)
    (out / "mkdocs.yml").write_text(MKDOCS_YML.format(nav=nav))
    print(f"wrote {len(pages)} pages to {out}")

    if not args.no_build:
        mk = ROOT / ".venv/bin/mkdocs"
        subprocess.run([str(mk), "build", "-q", "-f", str(out / "mkdocs.yml")], check=True)
        print(f"site: {out / 'site/index.html'}\nserve: {mk} serve -f {out / 'mkdocs.yml'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
