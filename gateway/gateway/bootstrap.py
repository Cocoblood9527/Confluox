from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, TextIO


@dataclass(frozen=True)
class BootstrapConfig:
    data_dir: str
    auth_token: str
    allowed_origin: str


def read_bootstrap_config(stream: TextIO) -> BootstrapConfig:
    line = stream.readline()
    if line == "":
        raise ValueError("bootstrap payload is required")

    payload_text = line.strip()
    if payload_text == "":
        raise ValueError("bootstrap payload is required")

    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError as err:
        raise ValueError(f"invalid bootstrap json: {err.msg}") from err

    if not isinstance(parsed, Mapping):
        raise ValueError("bootstrap payload must be object")

    data_dir = _require_str(parsed, "data_dir")
    auth_token = _require_str(parsed, "auth_token")
    allowed_origin = _require_str(parsed, "allowed_origin")
    _validate_allowed_origin(allowed_origin)
    return BootstrapConfig(
        data_dir=data_dir,
        auth_token=auth_token,
        allowed_origin=allowed_origin,
    )


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{key} is required")
    return value


def _validate_allowed_origin(value: str) -> None:
    if value == "*":
        raise ValueError("allowed_origin cannot be wildcard '*'")
