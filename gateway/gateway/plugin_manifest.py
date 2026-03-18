from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


PLUGIN_TYPES = {"api", "worker"}


@dataclass(frozen=True)
class PluginManifest:
    type: str
    name: str | None
    entry: str | None
    runtime: str | None
    permissions: dict[str, list[str]]
    command: list[str] | None
    sandbox_profile: str | None


def parse_plugin_manifest(payload: Mapping[str, Any]) -> PluginManifest:
    plugin_type = payload.get("type")
    if not isinstance(plugin_type, str) or plugin_type not in PLUGIN_TYPES:
        raise ValueError("type must be one of: api, worker")

    name = payload.get("name")
    if name is not None:
        if not isinstance(name, str) or name == "":
            raise ValueError("name must be non-empty string")

    entry = payload.get("entry")
    if plugin_type == "api":
        if not isinstance(entry, str) or entry.count(":") != 1:
            raise ValueError("entry must be '<module>:<function>'")
        module_name, function_name = entry.split(":", maxsplit=1)
        if module_name == "" or function_name == "":
            raise ValueError("entry must be '<module>:<function>'")
    elif entry is not None and (not isinstance(entry, str) or entry.count(":") != 1):
        raise ValueError("entry must be '<module>:<function>' when provided")

    command = payload.get("command")
    if plugin_type == "worker":
        if not isinstance(command, list) or len(command) == 0:
            raise ValueError("command is required for worker plugins")
        if any(not isinstance(part, str) or part == "" for part in command):
            raise ValueError("command must be a list of non-empty strings")
    elif command is not None:
        raise ValueError("command is only valid for worker plugins")

    runtime = payload.get("runtime")
    if runtime is not None and (not isinstance(runtime, str) or runtime == ""):
        raise ValueError("runtime must be non-empty string when provided")

    sandbox_profile = payload.get("sandbox_profile")
    if sandbox_profile is not None:
        if not isinstance(sandbox_profile, str) or sandbox_profile == "":
            raise ValueError("sandbox_profile must be non-empty string when provided")
        if plugin_type != "worker":
            raise ValueError("sandbox_profile is only valid for worker plugins")

    permissions_raw = payload.get("permissions", {})
    if not isinstance(permissions_raw, Mapping):
        raise ValueError("permissions must be an object")
    permissions: dict[str, list[str]] = {}
    for key, value in permissions_raw.items():
        if not isinstance(key, str) or key == "":
            raise ValueError("permissions keys must be non-empty strings")
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError("permissions values must be arrays of strings")
        permissions[key] = list(value)

    return PluginManifest(
        type=plugin_type,
        name=name,
        entry=entry,
        runtime=runtime,
        permissions=permissions,
        command=list(command) if isinstance(command, list) else None,
        sandbox_profile=sandbox_profile,
    )
