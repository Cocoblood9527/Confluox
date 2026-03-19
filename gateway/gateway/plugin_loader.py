from __future__ import annotations

import importlib.util
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import httpx
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from gateway.plugin_manifest import parse_plugin_manifest
from gateway.plugin_policy import (
    ApiPluginExecutionPolicy,
    ApiPluginTrustPolicy,
    evaluate_api_plugin_execution_mode,
    evaluate_api_plugin_trust,
)


_API_OUT_OF_PROCESS_HEALTH_PATH = "/__confluox/health"
_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


@dataclass
class PluginContext:
    app: FastAPI
    data_dir: str
    auth: Any
    process_manager: Any
    resource_resolver: Callable[[str], str]


@dataclass(frozen=True)
class PluginDescriptor:
    name: str
    plugin_dir: Path
    module_path: Path
    function_name: str
    trusted: bool
    trust_source: str
    execution_mode: str
    command: list[str] | None
    route_prefix: str


def discover_api_plugins(
    plugins_dir: str | Path,
    *,
    trust_policy: ApiPluginTrustPolicy | None = None,
    execution_policy: ApiPluginExecutionPolicy | None = None,
) -> list[PluginDescriptor]:
    base_dir = Path(plugins_dir)
    if not base_dir.exists():
        return []
    policy = trust_policy or ApiPluginTrustPolicy(trusted_roots=(base_dir,))
    exec_policy = execution_policy or ApiPluginExecutionPolicy(allowed_modes=("in_process",))

    descriptors: list[PluginDescriptor] = []
    for plugin_dir in sorted(base_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = parse_plugin_manifest(manifest_raw)
        if manifest.type != "api":
            continue

        if manifest.entry is None:
            raise ValueError("entry must be '<module>:<function>'")
        entry = manifest.entry
        module_name, function_name = entry.split(":", maxsplit=1)
        plugin_name = manifest.name or plugin_dir.name
        trust_decision = evaluate_api_plugin_trust(
            plugin_dir,
            plugin_name=plugin_name,
            policy=policy,
        )
        if not trust_decision.trusted:
            raise ValueError(f"untrusted api plugin: {plugin_name}")
        execution_decision = evaluate_api_plugin_execution_mode(
            manifest.execution_mode,
            policy=exec_policy,
        )
        if not execution_decision.allowed:
            raise ValueError(
                f"api execution mode not allowed: {plugin_name} ({execution_decision.normalized_mode})"
            )

        descriptors.append(
            PluginDescriptor(
                name=plugin_name,
                plugin_dir=plugin_dir,
                module_path=plugin_dir / f"{module_name}.py",
                function_name=function_name,
                trusted=trust_decision.trusted,
                trust_source=trust_decision.trust_source,
                execution_mode=execution_decision.normalized_mode,
                command=list(manifest.command) if isinstance(manifest.command, list) else None,
                route_prefix=f"/api/{plugin_name}",
            )
        )

    return descriptors


def activate_plugin_descriptors(
    descriptors: Iterable[PluginDescriptor],
    context: PluginContext,
    *,
    out_of_process_boot_timeout_seconds: float = 3.0,
) -> list[str]:
    loaded: list[str] = []
    for descriptor in descriptors:
        if not descriptor.trusted:
            raise ValueError(f"untrusted api plugin: {descriptor.name}")
        if descriptor.execution_mode == "in_process":
            module = _load_module(descriptor.module_path, plugin_name=descriptor.plugin_dir.name)
            setup = getattr(module, descriptor.function_name)
            setup(context)
        elif descriptor.execution_mode == "out_of_process":
            _activate_out_of_process_descriptor(
                descriptor,
                context=context,
                boot_timeout_seconds=out_of_process_boot_timeout_seconds,
            )
        else:
            raise ValueError(f"invalid api execution mode: {descriptor.execution_mode}")
        loaded.append(descriptor.name)
    return loaded


def load_api_plugins(plugins_dir: str | Path, context: PluginContext) -> list[str]:
    descriptors = discover_api_plugins(plugins_dir)
    return activate_plugin_descriptors(descriptors, context)


def _load_module(module_path: Path, plugin_name: str):
    module_key = f"gateway_plugin_{plugin_name}"
    spec = importlib.util.spec_from_file_location(module_key, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load plugin module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _activate_out_of_process_descriptor(
    descriptor: PluginDescriptor,
    *,
    context: PluginContext,
    boot_timeout_seconds: float,
) -> None:
    if context.process_manager is None:
        raise ValueError(
            f"api_oop_process_manager_required: plugin '{descriptor.name}' requires process manager"
        )
    if descriptor.command is None:
        raise ValueError(f"api_oop_command_missing: plugin '{descriptor.name}' has no command")

    reservation, port = _bind_loopback_ephemeral_port()
    reservation.close()
    child_env = dict(os.environ)
    child_env["CONFLUOX_PLUGIN_PORT"] = str(port)
    child_env["CONFLUOX_PLUGIN_PREFIX"] = descriptor.route_prefix
    process = context.process_manager.spawn(
        descriptor.command,
        env=child_env,
        cwd=str(descriptor.plugin_dir),
    )

    _wait_for_out_of_process_health(
        process=process,
        plugin_name=descriptor.name,
        port=port,
        boot_timeout_seconds=boot_timeout_seconds,
    )
    _register_proxy_route(context.app, descriptor=descriptor, port=port)


def _bind_loopback_ephemeral_port() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    return sock, int(sock.getsockname()[1])


def _wait_for_out_of_process_health(
    *,
    process,
    plugin_name: str,
    port: int,
    boot_timeout_seconds: float,
) -> None:
    timeout_seconds = max(0.05, float(boot_timeout_seconds))
    deadline = time.monotonic() + timeout_seconds
    health_url = f"http://127.0.0.1:{port}{_API_OUT_OF_PROCESS_HEALTH_PATH}"
    last_error: str | None = None

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError(
                f"api_oop_process_exited: plugin '{plugin_name}' exited with code {process.returncode}"
            )
        try:
            response = httpx.get(health_url, timeout=0.2)
            if response.status_code == 200:
                return
            last_error = f"health status {response.status_code}"
        except Exception as err:  # pragma: no cover - depends on host/socket timing
            last_error = str(err)
        time.sleep(0.05)

    detail = "" if last_error is None else f" ({last_error})"
    raise ValueError(
        f"api_oop_boot_timeout: plugin '{plugin_name}' did not become healthy within {timeout_seconds:.2f}s{detail}"
    )


def _register_proxy_route(app: FastAPI, *, descriptor: PluginDescriptor, port: int) -> None:
    router = APIRouter(prefix=descriptor.route_prefix)

    @router.api_route("", methods=_PROXY_METHODS)
    @router.api_route("/{path:path}", methods=_PROXY_METHODS)
    async def proxy(request: Request, path: str = ""):
        target_path = descriptor.route_prefix if path == "" else f"{descriptor.route_prefix}/{path}"
        target_url = f"http://127.0.0.1:{port}{target_path}"
        body = await request.body()
        headers = _filter_request_headers(request.headers)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                upstream = await client.request(
                    request.method,
                    target_url,
                    params=request.query_params,
                    content=body if len(body) > 0 else None,
                    headers=headers,
                )
        except Exception as err:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "api_oop_upstream_unavailable",
                    "plugin": descriptor.name,
                    "detail": str(err),
                },
            )

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=_filter_response_headers(upstream.headers),
        )

    app.include_router(router)


def _filter_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    blocked = {"host", "content-length", "connection"}
    return {key: value for key, value in headers.items() if key.lower() not in blocked}


def _filter_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    blocked = {"content-length", "connection", "transfer-encoding"}
    return {key: value for key, value in headers.items() if key.lower() not in blocked}
