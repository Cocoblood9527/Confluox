from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI


@dataclass
class PluginContext:
    app: FastAPI
    data_dir: str
    auth: Any
    process_manager: Any
    resource_resolver: Callable[[str], str]


def load_api_plugins(plugins_dir: str | Path, context: PluginContext) -> list[str]:
    base_dir = Path(plugins_dir)
    if not base_dir.exists():
        return []

    loaded: list[str] = []
    for plugin_dir in sorted(base_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("type") != "api":
            continue

        entry = str(manifest["entry"])
        module_name, function_name = entry.split(":", maxsplit=1)
        module_path = plugin_dir / f"{module_name}.py"
        module = _load_module(module_path, plugin_name=str(plugin_dir.name))
        setup = getattr(module, function_name)
        setup(context)
        loaded.append(str(manifest.get("name", plugin_dir.name)))

    return loaded


def _load_module(module_path: Path, plugin_name: str):
    module_key = f"gateway_plugin_{plugin_name}"
    spec = importlib.util.spec_from_file_location(module_key, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load plugin module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
