from __future__ import annotations

import json
import os
import socket
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI
import uvicorn

from .host_liveness import start_host_liveness_watch
from .routes import create_system_router


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


def create_app(on_shutdown: Callable[[], None] | None = None) -> FastAPI:
    app = FastAPI(title="Confluox Gateway", version="0.1.0")
    app.include_router(create_system_router(on_shutdown=on_shutdown))
    return app


def create_server(app: FastAPI, *, log_level: str = "info") -> uvicorn.Server:
    config = uvicorn.Config(app=app, log_level=log_level)
    return uvicorn.Server(config=config)


def run_server_with_socket(server: uvicorn.Server, sock: socket.socket) -> None:
    server.run(sockets=[sock])


def build_host_exit_callback(
    *,
    server: uvicorn.Server,
    ready_file: str | Path,
    terminate_all: Callable[[], None],
) -> Callable[[], None]:
    ready_path = Path(ready_file)

    def on_host_exit() -> None:
        terminate_all()
        ready_path.unlink(missing_ok=True)
        server.should_exit = True

    return on_host_exit


async def watch_host_and_shutdown(
    *,
    host_pid: int,
    server: uvicorn.Server,
    ready_file: str | Path,
    terminate_all: Callable[[], None],
    poll_interval: float = 1.0,
) -> None:
    on_host_exit = build_host_exit_callback(
        server=server,
        ready_file=ready_file,
        terminate_all=terminate_all,
    )
    await start_host_liveness_watch(
        host_pid=host_pid,
        on_host_exit=on_host_exit,
        poll_interval=poll_interval,
    )
