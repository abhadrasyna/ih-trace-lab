import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYPLOT = re.compile(r"matplotlib\.pyplot|from\s+matplotlib\s+import\s+[^\n]*\bpyplot\b")
HEX = re.compile(r"""["']#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})["']""")


def _sources() -> list[Path]:
    charts, scripts = ROOT / "src/lib/charts", ROOT / "scripts"
    assert charts.is_dir() and scripts.is_dir(), "guard roots missing"
    files = sorted(p for d in (charts, scripts) for p in d.rglob("*.py") if "__pycache__" not in p.parts)
    assert any(p.parent == charts for p in files), "no chart sources found"
    return files


def _offenders(pattern: re.Pattern, skip_theme: bool = False) -> list[str]:
    return [
        str(p.relative_to(ROOT))
        for p in _sources()
        if not (skip_theme and p.name == "theme.py" and p.parent.name == "charts")
        and pattern.search(p.read_text(encoding="utf-8"))
    ]


def test_no_pyplot_in_src_or_scripts():
    assert _offenders(PYPLOT) == []


def test_no_hex_outside_theme():
    assert _offenders(HEX, skip_theme=True) == []


def test_guard_patterns_detect_violations():
    assert PYPLOT.search("import matplotlib.pyplot as plt")
    assert PYPLOT.search("from matplotlib import pyplot")
    assert HEX.search('color="#1a2B3c"')
    assert HEX.search('"#1a2b3c80"') and HEX.search('"#fff"') and HEX.search('"#fff8"')
    assert not HEX.search("#12345") and not HEX.search("# fixes #1234") and not HEX.search("#cafe")
