from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(getattr(sys, "_MEIPASS"))
    elif bool(getattr(sys, "frozen", False)):
        base_path = Path(sys.executable).resolve().parent
    else:
        base_path = Path(__file__).resolve().parent.parent

    return str(base_path / relative_path)
