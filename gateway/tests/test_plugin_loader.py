from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import threading

import pytest
from fastapi.testclient import TestClient

from gateway.main import create_app
from gateway.plugin_policy import ApiPluginExecutionPolicy, ApiPluginTrustPolicy
from gateway.plugin_loader import (
    PluginContext,
    activate_plugin_descriptors,
    discover_api_plugins,
    register_lazy_api_plugin_activation,
)
from gateway.plugin_activation import PluginActivationController
from gateway.process_manager import ProcessManager


_OOP_SERVER_SCRIPT_PATH = Path(__file__).resolve().parent / "fixtures" / "oop_server.py"
# macOS CI can be significantly slower when spawning repeated subprocesses.
_OOP_BOOT_TIMEOUT_SECONDS = 20.0


def _oop_server_command(
    *,
    startup_delay_seconds: float = 0.0,
    fixed_expected_token: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(_OOP_SERVER_SCRIPT_PATH),
        "--startup-delay",
        str(startup_delay_seconds),
    ]
    if fixed_expected_token is not None:
        command.extend(["--fixed-expected-token", fixed_expected_token])
    return command


class _AliveProcess:
    returncode: int | None = None

    def poll(self) -> int | None:
        return None


class _StubProcessManager:
    def __init__(self) -> None:
        self.spawn_calls: list[dict[str, object]] = []

    def spawn(
        self,
        args,
        *,
        env=None,
        cwd=None,
        preexec_fn=None,
    ) -> _AliveProcess:
        self.spawn_calls.append(
            {
                "args": list(args),
                "env": dict(env) if env is not None else None,
                "cwd": cwd,
                "preexec_fn": preexec_fn,
            }
        )
        return _AliveProcess()

    def terminate_all(self, timeout: float = 3.0) -> None:  # pragma: no cover - no-op helper
        return


class _FixedPortReservation:
    def close(self) -> None:
        return


@contextmanager
def _run_local_oop_stub_server(route_prefix: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A003 - stdlib signature
            return

        def _json(self, status: int, payload: dict[str, str]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802 - stdlib signature
            if self.path == "/__confluox/health":
                self._json(200, {"status": "ok"})
                return
            if self.path == route_prefix or self.path.startswith(route_prefix + "/"):
                self._json(200, {"plugin": "api_oop", "path": self.path})
                return
            self._json(404, {"error": "not_found"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)


def _pin_out_of_process_port(monkeypatch: pytest.MonkeyPatch, port: int) -> None:
    monkeypatch.setattr(
        "gateway.plugin_loader._bind_loopback_ephemeral_port",
        lambda: (_FixedPortReservation(), port),
    )


def _make_unused_loopback_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def test_discovery_does_not_import_entry_modules(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "lazy_api"
    marker_file = tmp_path / "imported.marker"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "type": "api",
        "entry": "entry:setup",
        "name": "lazy_api",
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                f"open({repr(str(marker_file))}, 'w', encoding='utf-8').write('imported')",
                "",
                "def setup(context):",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    descriptors = discover_api_plugins(plugins_dir)

    assert [descriptor.name for descriptor in descriptors] == ["lazy_api"]
    assert marker_file.exists() is False


def test_first_request_triggers_lazy_activation(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "example_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "type": "api",
        "entry": "entry:setup",
        "name": "example_api",
    }
    (plugin_dir / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "",
                "def setup(context):",
                "    router = APIRouter(prefix='/api/example_api')",
                "",
                "    @router.get('')",
                "    def read_example():",
                "        return {'plugin': 'example_api'}",
                "",
                "    context.app.include_router(router)",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=None,
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(plugins_dir)
    activation = PluginActivationController(plugin_names=[descriptor.name for descriptor in descriptors])
    register_lazy_api_plugin_activation(
        app=app,
        descriptors=descriptors,
        context=context,
        activation=activation,
    )
    client = TestClient(app)

    before = activation.snapshot()["example_api"]
    assert before.state == "inactive"

    response = client.get("/api/example_api")
    assert response.status_code == 200
    assert response.json() == {"plugin": "example_api"}

    after = activation.snapshot()["example_api"]
    assert after.state == "active"


def test_parallel_first_requests_activate_plugin_only_once(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "parallel_api"
    activation_counter = tmp_path / "activation-count.txt"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "type": "api",
        "entry": "entry:setup",
        "name": "parallel_api",
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                "import time",
                "from fastapi import APIRouter",
                "",
                "def setup(context):",
                "    time.sleep(0.1)",
                f"    with open({repr(str(activation_counter))}, 'a', encoding='utf-8') as marker:",
                "        marker.write('activated\\n')",
                "    router = APIRouter(prefix='/api/parallel_api')",
                "",
                "    @router.get('')",
                "    def read_example():",
                "        return {'plugin': 'parallel_api'}",
                "",
                "    context.app.include_router(router)",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=None,
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(plugins_dir)
    activation = PluginActivationController(plugin_names=[descriptor.name for descriptor in descriptors])
    register_lazy_api_plugin_activation(
        app=app,
        descriptors=descriptors,
        context=context,
        activation=activation,
    )
    client = TestClient(app)

    def request_once() -> tuple[int, dict[str, str]]:
        response = client.get("/api/parallel_api")
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(lambda _: request_once(), range(2))

    assert first[0] == 200
    assert second[0] == 200
    assert first[1]["plugin"] == "parallel_api"
    assert second[1]["plugin"] == "parallel_api"
    assert activation_counter.read_text(encoding="utf-8").splitlines() == ["activated"]


def test_discovery_ignores_non_api_plugins(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    api_dir = plugins_dir / "api_plugin"
    worker_dir = plugins_dir / "worker_plugin"
    api_dir.mkdir(parents=True, exist_ok=True)
    worker_dir.mkdir(parents=True, exist_ok=True)

    (api_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "api_plugin"}),
        encoding="utf-8",
    )
    (api_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    worker_marker = tmp_path / "worker-imported.marker"
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "entry": "entry:setup",
                "name": "worker_plugin",
                "command": ["python3", "-m", "worker.main"],
            }
        ),
        encoding="utf-8",
    )
    (worker_dir / "entry.py").write_text(
        "\n".join(
            [
                f"open({repr(str(worker_marker))}, 'w', encoding='utf-8').write('imported')",
                "def setup(context):",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    descriptors = discover_api_plugins(plugins_dir)

    assert [descriptor.name for descriptor in descriptors] == ["api_plugin"]
    assert worker_marker.exists() is False


def test_discovery_rejects_invalid_manifest_schema(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    bad_dir = plugins_dir / "bad_manifest"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "name": "bad_manifest",
                "entry": "entry:setup",
                "permissions": {"fs": "read:/tmp"},
            }
        ),
        encoding="utf-8",
    )
    (bad_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="permissions"):
        discover_api_plugins(plugins_dir)


def test_discovery_trusts_api_plugin_under_trusted_root(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "trusted_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "trusted_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    descriptors = discover_api_plugins(
        plugins_dir,
        trust_policy=ApiPluginTrustPolicy(trusted_roots=(plugins_dir,)),
    )

    assert [descriptor.name for descriptor in descriptors] == ["trusted_api"]
    assert descriptors[0].trusted is True
    assert descriptors[0].trust_source == "trusted_root"


def test_discovery_blocks_untrusted_api_plugin_by_default(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "untrusted_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "untrusted_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="untrusted api plugin"):
        discover_api_plugins(
            plugins_dir,
            trust_policy=ApiPluginTrustPolicy(trusted_roots=(tmp_path / "trusted",)),
        )


def test_discovery_allows_untrusted_plugin_when_explicitly_trusted(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "allowlisted_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "allowlisted_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    descriptors = discover_api_plugins(
        plugins_dir,
        trust_policy=ApiPluginTrustPolicy(
            trusted_roots=(tmp_path / "trusted",),
            trusted_plugins=("allowlisted_api",),
        ),
    )

    assert [descriptor.name for descriptor in descriptors] == ["allowlisted_api"]
    assert descriptors[0].trusted is True
    assert descriptors[0].trust_source == "explicit_plugin_allowlist"


def test_discovery_blocks_out_of_process_api_by_default(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="api execution mode not allowed"):
        discover_api_plugins(plugins_dir)


def test_discovery_allows_out_of_process_when_policy_allows(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )

    assert len(descriptors) == 1
    assert descriptors[0].execution_mode == "out_of_process"


def test_activation_starts_out_of_process_plugin_and_proxies_routes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    with _run_local_oop_stub_server("/api/api_oop") as upstream_port:
        _pin_out_of_process_port(monkeypatch, upstream_port)

        app = create_app()
        context = PluginContext(
            app=app,
            data_dir=str(tmp_path),
            auth=None,
            process_manager=_StubProcessManager(),
            resource_resolver=lambda relative_path: relative_path,
        )
        descriptors = discover_api_plugins(
            plugins_dir,
            execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
        )
        loaded = activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        )
        assert loaded == ["api_oop"]

        client = TestClient(app)
        response = client.get("/api/api_oop")
        assert response.status_code == 200
        assert response.json()["plugin"] == "api_oop"
        assert response.json()["path"] == "/api/api_oop"


def test_activation_ignores_proxy_env_for_local_out_of_process_routes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop_proxy_env"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop_proxy_env",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    # Local plugin transport should never depend on ambient proxy variables.
    monkeypatch.setenv("HTTP_PROXY", "http://10.255.255.1:12345")
    monkeypatch.setenv("HTTPS_PROXY", "http://10.255.255.1:12345")
    monkeypatch.setenv("ALL_PROXY", "http://10.255.255.1:12345")
    monkeypatch.setenv("NO_PROXY", "")

    with _run_local_oop_stub_server("/api/api_oop_proxy_env") as upstream_port:
        _pin_out_of_process_port(monkeypatch, upstream_port)

        app = create_app()
        context = PluginContext(
            app=app,
            data_dir=str(tmp_path),
            auth=None,
            process_manager=_StubProcessManager(),
            resource_resolver=lambda relative_path: relative_path,
        )
        descriptors = discover_api_plugins(
            plugins_dir,
            execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
        )
        loaded = activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=1.5,
        )
        assert loaded == ["api_oop_proxy_env"]

        client = TestClient(app)
        response = client.get("/api/api_oop_proxy_env")
        assert response.status_code == 200
        assert response.json()["path"] == "/api/api_oop_proxy_env"


def test_activation_reports_boot_timeout_for_out_of_process_plugin(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop_timeout"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop_timeout",
                "execution_mode": "out_of_process",
                "command": [sys.executable, "-c", "import time; time.sleep(10)"],
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    app = create_app()
    manager = ProcessManager()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=manager,
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )

    with pytest.raises(ValueError, match="api_oop_boot_timeout"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=0.2,
        )

    manager.terminate_all(timeout=1.5)


def test_activation_reports_process_crash_for_out_of_process_plugin(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop_crash"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop_crash",
                "execution_mode": "out_of_process",
                "command": [sys.executable, "-c", "import sys; sys.exit(7)"],
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    app = create_app()
    manager = ProcessManager()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=manager,
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )

    with pytest.raises(ValueError, match="api_oop_process_exited"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        )


def test_activation_reports_auth_failure_for_out_of_process_plugin(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop_auth_failure"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop_auth_failure",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(fixed_expected_token="not-the-host-token"),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    def _raise_auth_failure(**_kwargs):
        raise ValueError("api_oop_auth_failed: plugin 'api_oop_auth_failure' rejected host auth token")

    monkeypatch.setattr("gateway.plugin_loader._wait_for_out_of_process_health", _raise_auth_failure)

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=_StubProcessManager(),
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )

    with pytest.raises(ValueError, match="api_oop_auth_failed"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        )


def test_activation_rejects_when_out_of_process_plugin_quota_exceeded(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    for plugin_name in ("api_oop_one", "api_oop_two"):
        plugin_dir = plugins_dir / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "type": "api",
                    "entry": "entry:setup",
                    "name": plugin_name,
                    "execution_mode": "out_of_process",
                    "command": _oop_server_command(),
                }
            ),
            encoding="utf-8",
        )
        (plugin_dir / "entry.py").write_text(
            "def setup(context):\n    pass\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "gateway.plugin_loader._wait_for_out_of_process_health",
        lambda **_kwargs: None,
    )

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=_StubProcessManager(),
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )

    with pytest.raises(ValueError, match="api_oop_quota_exceeded"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
            out_of_process_max_active_plugins=1,
        )


def test_proxy_reports_structured_error_when_out_of_process_upstream_unavailable(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "gateway.plugin_loader._wait_for_out_of_process_health",
        lambda **_kwargs: None,
    )
    _pin_out_of_process_port(monkeypatch, _make_unused_loopback_port())

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=_StubProcessManager(),
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )
    activate_plugin_descriptors(
        descriptors,
        context,
        out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
    )

    client = TestClient(app)
    response = client.get("/api/api_oop")
    assert response.status_code == 502
    assert response.json()["error"] == "api_oop_upstream_unavailable"
    assert response.json()["plugin"] == "api_oop"


def test_proxy_opens_circuit_after_repeated_out_of_process_failures(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "api_oop"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "api",
                "entry": "entry:setup",
                "name": "api_oop",
                "execution_mode": "out_of_process",
                "command": _oop_server_command(),
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "def setup(context):\n    pass\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "gateway.plugin_loader._wait_for_out_of_process_health",
        lambda **_kwargs: None,
    )
    _pin_out_of_process_port(monkeypatch, _make_unused_loopback_port())

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=_StubProcessManager(),
        resource_resolver=lambda relative_path: relative_path,
    )
    descriptors = discover_api_plugins(
        plugins_dir,
        execution_policy=ApiPluginExecutionPolicy(allowed_modes=("in_process", "out_of_process")),
    )
    activate_plugin_descriptors(
        descriptors,
        context,
        out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        out_of_process_proxy_circuit_failure_threshold=2,
        out_of_process_proxy_circuit_open_seconds=5.0,
    )

    client = TestClient(app)
    first = client.get("/api/api_oop")
    second = client.get("/api/api_oop")
    third = client.get("/api/api_oop")

    assert first.status_code == 502
    assert second.status_code == 503
    assert second.json()["error"] == "api_oop_circuit_open"
    assert third.status_code == 503
    assert third.json()["error"] == "api_oop_circuit_open"
