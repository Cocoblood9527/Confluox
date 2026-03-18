from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from fastapi import FastAPI
from gateway.plugin_manifest import parse_plugin_manifest


@dataclass
class PluginContext:
    app: FastAPI
    data_dir: str
    auth: Any
    process_manager: Any
    resource_resolver: Callable[[str], str]


@dataclass(frozen=True)
class PluginDescriptor:
    name: str
    plugin_dir: Path
    module_path: Path
    function_name: str


def discover_api_plugins(plugins_dir: str | Path) -> list[PluginDescriptor]:
    base_dir = Path(plugins_dir)
    if not base_dir.exists():
        return []

    descriptors: list[PluginDescriptor] = []
    for plugin_dir in sorted(base_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = parse_plugin_manifest(manifest_raw)
        if manifest.type != "api":
            continue

        if manifest.entry is None:
            raise ValueError("entry must be '<module>:<function>'")
        entry = manifest.entry
        module_name, function_name = entry.split(":", maxsplit=1)
        descriptors.append(
            PluginDescriptor(
                name=manifest.name or plugin_dir.name,
                plugin_dir=plugin_dir,
                module_path=plugin_dir / f"{module_name}.py",
                function_name=function_name,
            )
        )

    return descriptors


def activate_plugin_descriptors(
    descriptors: Iterable[PluginDescriptor],
    context: PluginContext,
) -> list[str]:
    loaded: list[str] = []
    for descriptor in descriptors:
        module = _load_module(descriptor.module_path, plugin_name=descriptor.plugin_dir.name)
        setup = getattr(module, descriptor.function_name)
        setup(context)
        loaded.append(descriptor.name)
    return loaded


def load_api_plugins(plugins_dir: str | Path, context: PluginContext) -> list[str]:
    descriptors = discover_api_plugins(plugins_dir)
    return activate_plugin_descriptors(descriptors, context)


def _load_module(module_path: Path, plugin_name: str):
    module_key = f"gateway_plugin_{plugin_name}"
    spec = importlib.util.spec_from_file_location(module_key, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load plugin module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
