from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from fastapi import FastAPI
from gateway.plugin_manifest import parse_plugin_manifest
from gateway.plugin_policy import (
    ApiPluginExecutionPolicy,
    ApiPluginTrustPolicy,
    evaluate_api_plugin_execution_mode,
    evaluate_api_plugin_trust,
)


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
    trusted: bool
    trust_source: str
    execution_mode: str


def discover_api_plugins(
    plugins_dir: str | Path,
    *,
    trust_policy: ApiPluginTrustPolicy | None = None,
    execution_policy: ApiPluginExecutionPolicy | None = None,
) -> list[PluginDescriptor]:
    base_dir = Path(plugins_dir)
    if not base_dir.exists():
        return []
    policy = trust_policy or ApiPluginTrustPolicy(trusted_roots=(base_dir,))
    exec_policy = execution_policy or ApiPluginExecutionPolicy(allowed_modes=("in_process",))

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
        plugin_name = manifest.name or plugin_dir.name
        trust_decision = evaluate_api_plugin_trust(
            plugin_dir,
            plugin_name=plugin_name,
            policy=policy,
        )
        if not trust_decision.trusted:
            raise ValueError(f"untrusted api plugin: {plugin_name}")
        execution_decision = evaluate_api_plugin_execution_mode(
            manifest.execution_mode,
            policy=exec_policy,
        )
        if not execution_decision.allowed:
            raise ValueError(
                f"api execution mode not allowed: {plugin_name} ({execution_decision.normalized_mode})"
            )

        descriptors.append(
            PluginDescriptor(
                name=plugin_name,
                plugin_dir=plugin_dir,
                module_path=plugin_dir / f"{module_name}.py",
                function_name=function_name,
                trusted=trust_decision.trusted,
                trust_source=trust_decision.trust_source,
                execution_mode=execution_decision.normalized_mode,
            )
        )

    return descriptors


def activate_plugin_descriptors(
    descriptors: Iterable[PluginDescriptor],
    context: PluginContext,
) -> list[str]:
    loaded: list[str] = []
    for descriptor in descriptors:
        if not descriptor.trusted:
            raise ValueError(f"untrusted api plugin: {descriptor.name}")
        if descriptor.execution_mode != "in_process":
            raise ValueError(
                f"api execution mode '{descriptor.execution_mode}' is not supported in current runtime"
            )
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
