from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Config:
    data_dir: str
    auth_token: str
    ready_file: str
    host_pid: int
    allowed_origin: str


def parse_config(
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    source_env = dict(os.environ) if env is None else dict(env)

    parser = argparse.ArgumentParser(prog="confluox-gateway")
    parser.add_argument("--data-dir", default=source_env.get("CONFLUOX_DATA_DIR"))
    parser.add_argument("--auth-token", default=source_env.get("CONFLUOX_AUTH_TOKEN"))
    parser.add_argument("--ready-file", default=source_env.get("CONFLUOX_READY_FILE"))
    parser.add_argument("--host-pid", type=int, default=source_env.get("CONFLUOX_HOST_PID"))
    parser.add_argument(
        "--allowed-origin", default=source_env.get("CONFLUOX_ALLOWED_ORIGIN")
    )

    parsed = parser.parse_args(list(args or []))

    config = Config(
        data_dir=_require(parsed.data_dir, "data_dir"),
        auth_token=_require(parsed.auth_token, "auth_token"),
        ready_file=_require(parsed.ready_file, "ready_file"),
        host_pid=_require_int(parsed.host_pid, "host_pid"),
        allowed_origin=_require(parsed.allowed_origin, "allowed_origin"),
    )
    _validate_allowed_origin(config.allowed_origin)
    return config


def _require(value: str | None, name: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return value


def _require_int(value: int | None, name: str) -> int:
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def _validate_allowed_origin(value: str) -> None:
    if value == "*":
        raise ValueError("allowed_origin cannot be wildcard '*'")
