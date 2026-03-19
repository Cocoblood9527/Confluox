import json

from fastapi.testclient import TestClient

from gateway.main import configure_api_plugins_for_app, create_app
from gateway.plugin_loader import PluginContext


def test_configure_api_plugins_keeps_system_routes_healthy_without_activation(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "lazy_main_api"
    marker_file = tmp_path / "activated.marker"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "lazy_main_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                f"open({repr(str(marker_file))}, 'w', encoding='utf-8').write('activated')",
                "def setup(context):",
                "    pass",
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
    activation = configure_api_plugins_for_app(
        app=app,
        plugins_dir=plugins_dir,
        context=context,
    )
    client = TestClient(app)

    health = client.get("/api/system/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert marker_file.exists() is False
    assert activation.snapshot()["lazy_main_api"].state == "inactive"


def test_configure_api_plugins_activates_plugin_on_first_request(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "lazy_main_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "lazy_main_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "",
                "def setup(context):",
                "    router = APIRouter(prefix='/api/lazy_main_api')",
                "",
                "    @router.get('')",
                "    def read_example():",
                "        return {'plugin': 'lazy_main_api'}",
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
    activation = configure_api_plugins_for_app(
        app=app,
        plugins_dir=plugins_dir,
        context=context,
    )
    client = TestClient(app)

    response = client.get("/api/lazy_main_api")
    assert response.status_code == 200
    assert response.json() == {"plugin": "lazy_main_api"}
    assert activation.snapshot()["lazy_main_api"].state == "active"


def test_plugin_activation_status_endpoint_returns_per_plugin_state(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "diag_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "diag_api"}),
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
        process_manager=None,
        resource_resolver=lambda relative_path: relative_path,
    )
    configure_api_plugins_for_app(
        app=app,
        plugins_dir=plugins_dir,
        context=context,
    )
    client = TestClient(app)

    response = client.get("/api/system/plugin-activation")
    assert response.status_code == 200
    assert response.json()["plugins"]["diag_api"]["state"] == "inactive"


def test_plugin_activation_status_endpoint_shows_failure_code_and_message(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "broken_api"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"type": "api", "entry": "entry:setup", "name": "broken_api"}),
        encoding="utf-8",
    )
    (plugin_dir / "entry.py").write_text(
        "\n".join(
            [
                "def setup(context):",
                "    raise RuntimeError('api_oop_boot_timeout: plugin failed to start')",
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
    configure_api_plugins_for_app(
        app=app,
        plugins_dir=plugins_dir,
        context=context,
    )
    client = TestClient(app)

    activation_result = client.get("/api/broken_api")
    assert activation_result.status_code == 503

    diagnostics = client.get("/api/system/plugin-activation")
    assert diagnostics.status_code == 200
    broken = diagnostics.json()["plugins"]["broken_api"]
    assert broken["state"] == "failed"
    assert broken["error_code"] == "api_oop_boot_timeout"
    assert "failed to start" in broken["error_message"]
