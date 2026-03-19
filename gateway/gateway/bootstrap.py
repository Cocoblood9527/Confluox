from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, TextIO


@dataclass(frozen=True)
class BootstrapConfig:
    data_dir: str
    auth_token: str
    allowed_origin: str
    auth_token_scope: str | None = None
    auth_token_ttl_seconds: int | None = None
    auth_token_issued_at: int | None = None


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
    auth_token_scope = _optional_str(parsed, "auth_token_scope")
    auth_token_ttl_seconds = _optional_int(parsed, "auth_token_ttl_seconds")
    auth_token_issued_at = _optional_int(parsed, "auth_token_issued_at")
    _validate_auth_token_metadata(
        scope=auth_token_scope,
        ttl_seconds=auth_token_ttl_seconds,
        issued_at=auth_token_issued_at,
    )
    _validate_allowed_origin(allowed_origin)
    return BootstrapConfig(
        data_dir=data_dir,
        auth_token=auth_token,
        allowed_origin=allowed_origin,
        auth_token_scope=auth_token_scope,
        auth_token_ttl_seconds=auth_token_ttl_seconds,
        auth_token_issued_at=auth_token_issued_at,
    )


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{key} is required")
    return value


def _optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{key} must be non-empty string when provided")
    return value


def _optional_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{key} must be integer when provided")
    return value


def _validate_auth_token_metadata(
    *,
    scope: str | None,
    ttl_seconds: int | None,
    issued_at: int | None,
) -> None:
    any_set = scope is not None or ttl_seconds is not None or issued_at is not None
    if not any_set:
        return
    if scope is None or ttl_seconds is None or issued_at is None:
        raise ValueError(
            "auth token metadata requires auth_token_scope, auth_token_ttl_seconds, auth_token_issued_at"
        )
    if ttl_seconds <= 0:
        raise ValueError("auth_token_ttl_seconds must be > 0")
    if issued_at < 0:
        raise ValueError("auth_token_issued_at must be >= 0")


def _validate_allowed_origin(value: str) -> None:
    if value == "*":
        raise ValueError("allowed_origin cannot be wildcard '*'")
