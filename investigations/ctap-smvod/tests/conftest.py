from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_script(script_name: str) -> ModuleType:
    module_name = f"ctap_smvod_{script_name.replace('/', '_').replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / script_name)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
