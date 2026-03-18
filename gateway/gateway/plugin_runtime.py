from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gateway.plugin_manifest import parse_plugin_manifest
from gateway.process_manager import ProcessManager


@dataclass(frozen=True)
class WorkerPluginDescriptor:
    name: str
    plugin_dir: Path
    command: list[str]
    runtime: str | None
    permissions: dict[str, list[str]]


@dataclass(frozen=True)
class WorkerRuntimeStatus:
    name: str
    pid: int | None
    running: bool
    command: list[str]
    runtime: str | None


def discover_worker_plugins(plugins_dir: str | Path) -> list[WorkerPluginDescriptor]:
    base_dir = Path(plugins_dir)
    if not base_dir.exists():
        return []

    descriptors: list[WorkerPluginDescriptor] = []
    for plugin_dir in sorted(base_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = parse_plugin_manifest(manifest_raw)
        if manifest.type != "worker":
            continue
        if manifest.command is None:
            raise ValueError("command is required for worker plugins")

        descriptors.append(
            WorkerPluginDescriptor(
                name=manifest.name or plugin_dir.name,
                plugin_dir=plugin_dir,
                command=list(manifest.command),
                runtime=manifest.runtime,
                permissions=dict(manifest.permissions),
            )
        )
    return descriptors


def start_worker_plugins(
    descriptors: list[WorkerPluginDescriptor],
    *,
    process_manager: ProcessManager,
) -> list[WorkerRuntimeStatus]:
    statuses: list[WorkerRuntimeStatus] = []
    for descriptor in descriptors:
        process = process_manager.spawn_worker(descriptor.name, descriptor.command)
        statuses.append(
            WorkerRuntimeStatus(
                name=descriptor.name,
                pid=process.pid,
                running=process.poll() is None,
                command=list(descriptor.command),
                runtime=descriptor.runtime,
            )
        )
    return statuses
