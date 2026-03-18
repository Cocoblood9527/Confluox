from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Config:
    ready_file: str
    host_pid: int


def parse_config(
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    source_env = dict(os.environ) if env is None else dict(env)

    parser = argparse.ArgumentParser(prog="confluox-gateway")
    parser.add_argument("--ready-file", default=source_env.get("CONFLUOX_READY_FILE"))
    parser.add_argument("--host-pid", type=int, default=source_env.get("CONFLUOX_HOST_PID"))

    parsed = parser.parse_args(list(args or []))

    config = Config(
        ready_file=_require(parsed.ready_file, "ready_file"),
        host_pid=_require_int(parsed.host_pid, "host_pid"),
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
