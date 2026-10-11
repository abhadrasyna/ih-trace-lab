"""Renumber MEC task IDs across docs in one simultaneous pass.

Old and new ID ranges overlap, so every ID is replaced in a single regex pass (never
sequentially). Slash shorthand such as ``MEC-6/7`` is remapped too. A comma list such as ``MEC-2, 5``
is ambiguous with ordinary prose numbers, so it raises: write it out as ``MEC-2, MEC-5`` first. Other
joiners (``MEC-5 and 6``, ``MEC-5-7``) are not detected; write each id with its ``MEC-`` prefix.
Ranges (``MEC-5 to MEC-7``) stay textually valid but may no longer be contiguous; review them.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.lib.logging.bootstrap import init_logging  # noqa: E402

_REF = re.compile(r"MEC-(\d+)((?:/\d+(?!\d|\.\d))*)")
_COMMA_LIST = re.compile(r"MEC-\d+(?:/\d+)*,\s*\d")
_HEADING = re.compile(r"^## MEC-(\d+) ", re.MULTILINE)


def renumber_text(text: str, mapping: dict[int, int]) -> str:
    """Replace every MEC id (and slash-shorthand ids) using mapping; unknown ids fail loudly."""
    if _COMMA_LIST.search(text):
        raise ValueError("ambiguous comma list after a MEC id; write each id with its MEC- prefix")

    def lookup(old: str) -> str:
        key = int(old)
        if key not in mapping:
            raise KeyError(f"MEC-{key} is not in the mapping")
        return str(mapping[key])

    def repl(match: re.Match[str]) -> str:
        tail = re.sub(r"\d+", lambda m: lookup(m.group(0)), match.group(2))
        if match.group(2):
            print(f"review shorthand: {match.group(0)} -> MEC-{lookup(match.group(1))}{tail}", file=sys.stderr)
        return f"MEC-{lookup(match.group(1))}{tail}"

    return _REF.sub(repl, text)


def sort_story_sections(text: str) -> str:
    """Sort '## MEC-n' sections of stories.md by n, keeping the preamble first.

    Sections are separated by a '---' line; separators are rebuilt between sections so none
    dangles at the end. Content after the last MEC heading is treated as part of that section.
    """
    starts = [m.start() for m in _HEADING.finditer(text)]
    if not starts:
        raise ValueError("no '## MEC-n' headings found")
    preamble, body = text[: starts[0]], text[starts[0]:]
    parts = re.split(r"(?m)^(?=## MEC-\d+ )", body)
    sections = [re.sub(r"\n+---\s*$", "", p.rstrip()) for p in parts if p.strip()]
    sections.sort(key=lambda p: int(_HEADING.match(p).group(1)))
    return preamble + "\n\n---\n\n".join(sections) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, help='JSON file: {"old": new, ...}')
    parser.add_argument("--stories", help="stories.md path whose sections are re-sorted after renumbering")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    mapping = {int(k): int(v) for k, v in json.loads(Path(args.mapping).read_text()).items()}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("mapping is not one-to-one")
    init_logging("mec-renumber_mec_tasks", to_file=False)
    if args.stories and Path(args.stories).resolve() not in {p.resolve() for p in args.files}:
        raise ValueError("--stories must also be listed in files")
    # Compute every result before writing so a failure cannot leave a half-renumbered tree
    # (re-running on partly renumbered files would apply the mapping twice).
    results = {}
    for path in args.files:
        new = renumber_text(path.read_text(), mapping)
        if args.stories and path.resolve() == Path(args.stories).resolve():
            new = sort_story_sections(new)
        results[path] = new
    for path, new in results.items():
        path.write_text(new)
        print(f"renumbered {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
