from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Config:
    ready_file: str
    host_pid: int
    trusted_api_plugin_roots: tuple[str, ...]
    trusted_api_plugins: tuple[str, ...]
    allowed_api_execution_modes: tuple[str, ...]


def parse_config(
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    source_env = dict(os.environ) if env is None else dict(env)

    parser = argparse.ArgumentParser(prog="confluox-gateway")
    parser.add_argument("--ready-file", default=source_env.get("CONFLUOX_READY_FILE"))
    parser.add_argument("--host-pid", type=int, default=source_env.get("CONFLUOX_HOST_PID"))
    parser.add_argument(
        "--trusted-api-plugin-root",
        action="append",
        dest="trusted_api_plugin_roots",
        default=None,
    )
    parser.add_argument(
        "--trusted-api-plugin",
        action="append",
        dest="trusted_api_plugins",
        default=None,
    )
    parser.add_argument(
        "--allowed-api-execution-mode",
        action="append",
        dest="allowed_api_execution_modes",
        default=None,
    )

    parsed = parser.parse_args(list(args or []))

    config = Config(
        ready_file=_require(parsed.ready_file, "ready_file"),
        host_pid=_require_int(parsed.host_pid, "host_pid"),
        trusted_api_plugin_roots=tuple(
            _split_csv(source_env.get("CONFLUOX_TRUSTED_API_PLUGIN_ROOTS"))
            + list(parsed.trusted_api_plugin_roots or [])
        ),
        trusted_api_plugins=tuple(
            _split_csv(source_env.get("CONFLUOX_TRUSTED_API_PLUGINS"))
            + list(parsed.trusted_api_plugins or [])
        ),
        allowed_api_execution_modes=tuple(
            _split_csv(source_env.get("CONFLUOX_ALLOWED_API_EXECUTION_MODES"))
            + list(parsed.allowed_api_execution_modes or [])
        ),
    )
    return config


def _require(value: str | None, name: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return value


def _require_int(value: int | None, name: str) -> int:
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def _split_csv(raw: str | None) -> list[str]:
    if raw is None or raw.strip() == "":
        return []
    return [item.strip() for item in raw.split(",") if item.strip() != ""]
