from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping, Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from gateway.auth import BearerAuthMiddleware
from gateway.bootstrap import read_bootstrap_config
from gateway.config import parse_config
from gateway.host_liveness import start_host_liveness_watch
from gateway.plugin_loader import (
    PluginContext,
    activate_plugin_descriptors,
    discover_api_plugins,
)
from gateway.plugin_policy import (
    ApiPluginExecutionPolicy,
    ApiPluginTrustPolicy,
    WorkerPermissionPolicy,
    WorkerSandboxProfilePolicy,
)
from gateway.plugin_runtime import discover_worker_plugins, start_worker_plugins
from gateway.process_manager import ProcessManager
from gateway.resource_resolver import get_resource_path
from gateway.routes import create_streaming_router, create_system_router


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
    app.include_router(create_streaming_router())
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


def register_ready_file_startup_hook(
    *,
    app: FastAPI,
    ready_file: str | Path,
    port: int,
    version: str = "0.1.0",
) -> None:
    ready_path = Path(ready_file)

    async def write_ready_file_on_startup() -> None:
        write_ready_file_atomic(
            ready_path,
            build_ready_payload(port=port, version=version),
        )

    app.router.on_startup.append(write_ready_file_on_startup)


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


def default_plugins_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins"


def default_worker_permission_policy() -> WorkerPermissionPolicy:
    return WorkerPermissionPolicy(
        allowlist={
            "network": ["loopback"],
            "fs": ["read:/tmp"],
        }
    )


def default_worker_sandbox_profile_policy() -> WorkerSandboxProfilePolicy:
    return WorkerSandboxProfilePolicy(
        allowed_profiles=("restricted", "strict"),
    )


def default_api_trust_policy(
    *,
    plugins_dir: Path,
    trusted_roots: Sequence[str] = (),
    trusted_plugins: Sequence[str] = (),
) -> ApiPluginTrustPolicy:
    roots = [plugins_dir]
    roots.extend(Path(root) for root in trusted_roots)
    return ApiPluginTrustPolicy(
        trusted_roots=tuple(roots),
        trusted_plugins=tuple(trusted_plugins),
    )


def default_api_execution_policy(
    *,
    allowed_modes: Sequence[str] = (),
) -> ApiPluginExecutionPolicy:
    if len(allowed_modes) == 0:
        return ApiPluginExecutionPolicy(allowed_modes=("in_process",))
    return ApiPluginExecutionPolicy(allowed_modes=tuple(allowed_modes))


def run_gateway(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    config = parse_config(args)
    bootstrap = read_bootstrap_config(sys.stdin)
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
        auth_token=bootstrap.auth_token,
        allowed_origin=bootstrap.allowed_origin,
    )

    plugin_context = PluginContext(
        app=app,
        data_dir=bootstrap.data_dir,
        auth=bootstrap.auth_token,
        process_manager=process_manager,
        resource_resolver=get_resource_path,
    )
    plugins_dir = default_plugins_dir()
    plugin_descriptors = discover_api_plugins(
        plugins_dir,
        trust_policy=default_api_trust_policy(
            plugins_dir=plugins_dir,
            trusted_roots=config.trusted_api_plugin_roots,
            trusted_plugins=config.trusted_api_plugins,
        ),
        execution_policy=default_api_execution_policy(
            allowed_modes=config.allowed_api_execution_modes,
        ),
    )
    activate_plugin_descriptors(
        plugin_descriptors,
        plugin_context,
        out_of_process_boot_timeout_seconds=config.api_out_of_process_boot_timeout_seconds,
        out_of_process_max_active_plugins=config.api_out_of_process_max_active_plugins,
        out_of_process_proxy_circuit_failure_threshold=config.api_out_of_process_circuit_failure_threshold,
        out_of_process_proxy_circuit_open_seconds=config.api_out_of_process_circuit_open_seconds,
    )
    worker_descriptors = discover_worker_plugins(plugins_dir)
    start_worker_plugins(
        worker_descriptors,
        process_manager=process_manager,
        permission_policy=default_worker_permission_policy(),
        sandbox_profile_policy=default_worker_sandbox_profile_policy(),
    )

    sock, port = bind_localhost_ephemeral_socket()
    register_ready_file_startup_hook(
        app=app,
        ready_file=ready_path,
        port=port,
    )

    server = create_server(app)
    server_ref["server"] = server

    host_watch_thread = threading.Thread(
        target=start_host_liveness_watch,
        kwargs={
            "stream": sys.stdin,
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


if __name__ == "__main__":
    run_gateway()
