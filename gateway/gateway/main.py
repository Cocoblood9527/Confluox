from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .auth import BearerAuthMiddleware
from .config import parse_config
from .host_liveness import is_host_alive, start_host_liveness_watch
from .plugin_loader import PluginContext, load_api_plugins
from .process_manager import ProcessManager
from .resource_resolver import get_resource_path
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


def create_app(
    *,
    on_shutdown: Callable[[], None] | None = None,
    auth_token: str | None = None,
    allowed_origin: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Confluox Gateway", version="0.1.0")
    app.include_router(create_system_router(on_shutdown=on_shutdown))
    if allowed_origin is not None:
        if allowed_origin == "*":
            raise ValueError("allowed_origin cannot be wildcard '*'")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[allowed_origin],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    if auth_token is not None:
        app.add_middleware(BearerAuthMiddleware, token=auth_token)
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


def default_plugins_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins"


def run_gateway(argv: list[str] | None = None) -> None:
    config = parse_config(argv or [])
    ready_path = Path(config.ready_file)
    ready_path.unlink(missing_ok=True)

    process_manager = ProcessManager()
    server_ref: dict[str, uvicorn.Server | None] = {"server": None}

    def terminate_all() -> None:
        process_manager.terminate_all()

    def on_shutdown() -> None:
        terminate_all()
        ready_path.unlink(missing_ok=True)
        server = server_ref["server"]
        if server is not None:
            server.should_exit = True

    app = create_app(
        on_shutdown=on_shutdown,
        auth_token=config.auth_token,
        allowed_origin=config.allowed_origin,
    )

    plugin_context = PluginContext(
        app=app,
        data_dir=config.data_dir,
        auth=config.auth_token,
        process_manager=process_manager,
        resource_resolver=get_resource_path,
    )
    load_api_plugins(default_plugins_dir(), plugin_context)

    sock, port = bind_localhost_ephemeral_socket()
    write_ready_file_atomic(ready_path, build_ready_payload(port=port))

    server = create_server(app)
    server_ref["server"] = server

    host_watch_thread = threading.Thread(
        target=_watch_host_pid,
        kwargs={
            "host_pid": config.host_pid,
            "on_host_exit": on_shutdown,
        },
        daemon=True,
    )
    host_watch_thread.start()

    try:
        run_server_with_socket(server, sock)
    finally:
        on_shutdown()
        sock.close()


def _watch_host_pid(*, host_pid: int, on_host_exit: Callable[[], None]) -> None:
    while True:
        if not is_host_alive(host_pid):
            on_host_exit()
            return
        time.sleep(1.0)


if __name__ == "__main__":
    run_gateway()
