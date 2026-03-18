import json

from fastapi.testclient import TestClient

from gateway.main import create_app
from gateway.plugin_loader import (
    PluginContext,
    activate_plugin_descriptors,
    discover_api_plugins,
)


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
        json.dumps({"type": "worker", "entry": "entry:setup", "name": "worker_plugin"}),
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
