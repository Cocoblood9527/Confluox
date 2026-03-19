from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Config:
    ready_file: str
    host_pid: int
    data_dir: str | None
    auth_token: str | None
    allowed_origin: str | None
    trusted_api_plugin_roots: tuple[str, ...]
    trusted_api_plugins: tuple[str, ...]
    allowed_api_execution_modes: tuple[str, ...]
    api_out_of_process_boot_timeout_seconds: float
    api_out_of_process_max_active_plugins: int
    api_out_of_process_circuit_failure_threshold: int
    api_out_of_process_circuit_open_seconds: float


def parse_config(
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    source_env = dict(os.environ) if env is None else dict(env)

    parser = argparse.ArgumentParser(prog="confluox-gateway")
    parser.add_argument("--ready-file", default=source_env.get("CONFLUOX_READY_FILE"))
    parser.add_argument("--host-pid", type=int, default=source_env.get("CONFLUOX_HOST_PID"))
    parser.add_argument("--data-dir", default=source_env.get("CONFLUOX_DATA_DIR"))
    parser.add_argument("--auth-token", default=source_env.get("CONFLUOX_AUTH_TOKEN"))
    parser.add_argument(
        "--allowed-origin",
        default=source_env.get("CONFLUOX_ALLOWED_ORIGIN"),
    )
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
    parser.add_argument(
        "--api-out-of-process-boot-timeout-seconds",
        type=float,
        default=source_env.get("CONFLUOX_API_OOP_BOOT_TIMEOUT_SECONDS"),
    )
    parser.add_argument(
        "--api-out-of-process-max-active-plugins",
        type=int,
        default=source_env.get("CONFLUOX_API_OOP_MAX_ACTIVE_PLUGINS"),
    )
    parser.add_argument(
        "--api-out-of-process-circuit-failure-threshold",
        type=int,
        default=source_env.get("CONFLUOX_API_OOP_CIRCUIT_FAILURE_THRESHOLD"),
    )
    parser.add_argument(
        "--api-out-of-process-circuit-open-seconds",
        type=float,
        default=source_env.get("CONFLUOX_API_OOP_CIRCUIT_OPEN_SECONDS"),
    )

    parsed = parser.parse_args(list(args or []))

    config = Config(
        ready_file=_require(parsed.ready_file, "ready_file"),
        host_pid=_require_int(parsed.host_pid, "host_pid"),
        data_dir=_optional_non_empty(parsed.data_dir),
        auth_token=_optional_non_empty(parsed.auth_token),
        allowed_origin=_optional_non_empty(parsed.allowed_origin),
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
        api_out_of_process_boot_timeout_seconds=_default_float(
            parsed.api_out_of_process_boot_timeout_seconds,
            default=3.0,
        ),
        api_out_of_process_max_active_plugins=_default_int(
            parsed.api_out_of_process_max_active_plugins,
            default=4,
        ),
        api_out_of_process_circuit_failure_threshold=_default_int(
            parsed.api_out_of_process_circuit_failure_threshold,
            default=3,
        ),
        api_out_of_process_circuit_open_seconds=_default_float(
            parsed.api_out_of_process_circuit_open_seconds,
            default=5.0,
        ),
    )
    _validate_positive_int(
        config.api_out_of_process_max_active_plugins,
        "api_out_of_process_max_active_plugins",
    )
    _validate_positive_int(
        config.api_out_of_process_circuit_failure_threshold,
        "api_out_of_process_circuit_failure_threshold",
    )
    _validate_positive_float(
        config.api_out_of_process_circuit_open_seconds,
        "api_out_of_process_circuit_open_seconds",
    )
    if config.allowed_origin == "*":
        raise ValueError("allowed_origin cannot be wildcard '*'")
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


def _optional_non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped


def _default_float(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _default_int(value: int | None, *, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _validate_positive_int(value: int, name: str) -> None:
    if value < 1:
        raise ValueError(f"{name} must be >= 1")


def _validate_positive_float(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
