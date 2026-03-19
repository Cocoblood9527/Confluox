from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gateway.plugin_manifest import parse_plugin_manifest
from gateway.plugin_policy import (
    PermissionPolicyViolation,
    WorkerPermissionPolicy,
    WorkerSandboxProfilePolicy,
    evaluate_worker_permissions,
    evaluate_worker_sandbox_profile,
)
from gateway.process_manager import ProcessManager


@dataclass(frozen=True)
class WorkerPluginDescriptor:
    name: str
    plugin_dir: Path
    command: list[str]
    runtime: str | None
    permissions: dict[str, list[str]]
    sandbox_profile: str | None


@dataclass(frozen=True)
class WorkerRuntimeStatus:
    name: str
    pid: int | None
    running: bool
    command: list[str]
    runtime: str | None
    rejected: bool
    policy_violations: list[PermissionPolicyViolation]


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
                sandbox_profile=manifest.sandbox_profile,
            )
        )
    return descriptors


def start_worker_plugins(
    descriptors: list[WorkerPluginDescriptor],
    *,
    process_manager: ProcessManager,
    permission_policy: WorkerPermissionPolicy | None = None,
    sandbox_profile_policy: WorkerSandboxProfilePolicy | None = None,
) -> list[WorkerRuntimeStatus]:
    statuses: list[WorkerRuntimeStatus] = []
    for descriptor in descriptors:
        if permission_policy is not None:
            decision = evaluate_worker_permissions(
                descriptor.permissions,
                policy=permission_policy,
            )
            if not decision.allowed:
                statuses.append(
                    WorkerRuntimeStatus(
                        name=descriptor.name,
                        pid=None,
                        running=False,
                        command=list(descriptor.command),
                        runtime=descriptor.runtime,
                        rejected=True,
                        policy_violations=list(decision.violations),
                    )
                )
                continue

        if sandbox_profile_policy is not None:
            sandbox_decision = evaluate_worker_sandbox_profile(
                descriptor.sandbox_profile,
                policy=sandbox_profile_policy,
            )
            if not sandbox_decision.allowed:
                statuses.append(
                    WorkerRuntimeStatus(
                        name=descriptor.name,
                        pid=None,
                        running=False,
                        command=list(descriptor.command),
                        runtime=descriptor.runtime,
                        rejected=True,
                        policy_violations=[
                            PermissionPolicyViolation(
                                code=violation.code,
                                namespace="sandbox_profile",
                                entry=violation.profile,
                                message=violation.message,
                            )
                            for violation in sandbox_decision.violations
                        ],
                    )
                )
                continue

        try:
            process = process_manager.spawn_worker(
                descriptor.name,
                descriptor.command,
                sandbox_profile=descriptor.sandbox_profile,
            )
        except ValueError as err:
            message = str(err)
            if message.startswith("worker_sandbox_not_supported"):
                statuses.append(
                    WorkerRuntimeStatus(
                        name=descriptor.name,
                        pid=None,
                        running=False,
                        command=list(descriptor.command),
                        runtime=descriptor.runtime,
                        rejected=True,
                        policy_violations=[
                            PermissionPolicyViolation(
                                code="sandbox_runtime_not_supported",
                                namespace="sandbox_profile",
                                entry=descriptor.sandbox_profile,
                                message=message,
                            )
                        ],
                    )
                )
                continue
            if message.startswith("worker_sandbox_unknown_profile"):
                statuses.append(
                    WorkerRuntimeStatus(
                        name=descriptor.name,
                        pid=None,
                        running=False,
                        command=list(descriptor.command),
                        runtime=descriptor.runtime,
                        rejected=True,
                        policy_violations=[
                            PermissionPolicyViolation(
                                code="sandbox_profile_unknown",
                                namespace="sandbox_profile",
                                entry=descriptor.sandbox_profile,
                                message=message,
                            )
                        ],
                    )
                )
                continue
            raise
        statuses.append(
            WorkerRuntimeStatus(
                name=descriptor.name,
                pid=process.pid,
                running=process.poll() is None,
                command=list(descriptor.command),
                runtime=descriptor.runtime,
                rejected=False,
                policy_violations=[],
            )
        )
    return statuses
