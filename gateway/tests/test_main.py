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
