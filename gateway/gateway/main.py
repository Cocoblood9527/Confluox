from __future__ import annotations

import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Any, Mapping


def bind_localhost_ephemeral_socket() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    return sock, port


def build_ready_payload(
    *,
    port: int,
    status: str = "ready",
    version: str = "0.1.0",
    pid: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "port": int(port),
        "pid": int(os.getpid() if pid is None else pid),
        "version": version,
    }
    return payload


def write_ready_file_atomic(path: str | Path, payload: Mapping[str, Any]) -> None:
    ready_path = Path(path)
    ready_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=ready_path.parent,
        prefix=f".{ready_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        json.dump(dict(payload), temp_file, ensure_ascii=True)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_name = temp_file.name

    os.replace(temp_name, ready_path)


def is_ready_payload(payload: Mapping[str, Any]) -> bool:
    return payload.get("status") == "ready"
