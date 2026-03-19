import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from gateway.main import create_app
from gateway.plugin_policy import ApiPluginExecutionPolicy, ApiPluginTrustPolicy
from gateway.plugin_loader import (
    PluginContext,
    activate_plugin_descriptors,
    discover_api_plugins,
)
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


def test_activation_happens_only_when_requested(tmp_path) -> None:
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
                "    router = APIRouter(prefix='/api/example')",
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
    client = TestClient(app)

    not_loaded = client.get("/api/example")
    assert not_loaded.status_code == 404

    loaded = activate_plugin_descriptors(descriptors, context)
    assert loaded == ["example_api"]

    response = client.get("/api/example")
    assert response.status_code == 200
    assert response.json() == {"plugin": "example_api"}


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


def test_activation_starts_out_of_process_plugin_and_proxies_routes(tmp_path) -> None:
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

    app = create_app()
    context = PluginContext(
        app=app,
        data_dir=str(tmp_path),
        auth=None,
        process_manager=ProcessManager(),
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

    context.process_manager.terminate_all(timeout=1.5)


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

    manager.terminate_all(timeout=1.5)


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


def test_activation_reports_auth_failure_for_out_of_process_plugin(tmp_path) -> None:
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

    with pytest.raises(ValueError, match="api_oop_auth_failed"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        )
    manager.terminate_all(timeout=1.5)


def test_activation_rejects_when_out_of_process_plugin_quota_exceeded(tmp_path) -> None:
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

    with pytest.raises(ValueError, match="api_oop_quota_exceeded"):
        activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
            out_of_process_max_active_plugins=1,
        )
    manager.terminate_all(timeout=1.5)


def test_proxy_reports_structured_error_when_out_of_process_upstream_unavailable(tmp_path) -> None:
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
    activate_plugin_descriptors(
        descriptors,
        context,
        out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
    )

    manager.terminate_all(timeout=1.5)
    client = TestClient(app)
    response = client.get("/api/api_oop")
    assert response.status_code == 502
    assert response.json()["error"] == "api_oop_upstream_unavailable"
    assert response.json()["plugin"] == "api_oop"


def test_proxy_opens_circuit_after_repeated_out_of_process_failures(tmp_path) -> None:
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
    activate_plugin_descriptors(
        descriptors,
        context,
        out_of_process_boot_timeout_seconds=_OOP_BOOT_TIMEOUT_SECONDS,
        out_of_process_proxy_circuit_failure_threshold=2,
        out_of_process_proxy_circuit_open_seconds=5.0,
    )

    manager.terminate_all(timeout=1.5)
    client = TestClient(app)
    first = client.get("/api/api_oop")
    second = client.get("/api/api_oop")
    third = client.get("/api/api_oop")

    assert first.status_code == 502
    assert second.status_code == 503
    assert second.json()["error"] == "api_oop_circuit_open"
    assert third.status_code == 503
    assert third.json()["error"] == "api_oop_circuit_open"
