"""Local bootstrap helpers for direct script execution."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
VENDOR_SRC = REPO_ROOT / "vendor" / "athena-mcp-server" / "src"

for candidate in (REPO_ROOT, VENDOR_SRC):
    candidate_str = str(candidate)
    if candidate.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)
