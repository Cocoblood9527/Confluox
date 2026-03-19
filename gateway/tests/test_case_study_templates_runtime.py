from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from gateway.main import create_app
from gateway.plugin_loader import (
    ApiPluginExecutionPolicy,
    PluginContext,
    activate_plugin_descriptors,
    discover_api_plugins,
)
from gateway.process_manager import ProcessManager


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "plugins/examples"


def _copy_example_template(
    *,
    template_dir_name: str,
    destination_plugins_dir: Path,
    destination_plugin_dir_name: str,
) -> Path:
    source_dir = EXAMPLES_ROOT / template_dir_name
    destination_dir = destination_plugins_dir / destination_plugin_dir_name
    shutil.copytree(source_dir, destination_dir)
    return destination_dir


def test_md_builder_template_roundtrip(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    _copy_example_template(
        template_dir_name="md_builder_template",
        destination_plugins_dir=plugins_dir,
        destination_plugin_dir_name="md_builder_plugin",
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
    descriptors = discover_api_plugins(plugins_dir)
    loaded = activate_plugin_descriptors(descriptors, context)

    assert loaded == ["md_builder"]

    client = TestClient(app)
    response = client.post("/api/md/build", json={"source_dir": "/tmp/docs"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source_dir"] == "/tmp/docs"
    assert payload["output"].endswith("/site/index.html")


def test_whisper_oop_template_roundtrip(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir = _copy_example_template(
        template_dir_name="whisper_oop_template",
        destination_plugins_dir=plugins_dir,
        destination_plugin_dir_name="whisper_oop_plugin",
    )

    manifest_path = plugin_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["command"] = [sys.executable, "-m", "entry"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    app = create_app()
    manager = ProcessManager()
    try:
        context = PluginContext(
            app=app,
            data_dir=str(tmp_path),
            auth=None,
            process_manager=manager,
            resource_resolver=lambda relative_path: relative_path,
        )
        descriptors = discover_api_plugins(
            plugins_dir,
            execution_policy=ApiPluginExecutionPolicy(
                allowed_modes=("in_process", "out_of_process")
            ),
        )
        loaded = activate_plugin_descriptors(
            descriptors,
            context,
            out_of_process_boot_timeout_seconds=2.0,
        )
        assert loaded == ["whisper_app"]

        client = TestClient(app)
        response = client.post(
            "/api/whisper_app/transcribe",
            json={"audio_path": "/tmp/example.wav"},
        )
        assert response.status_code == 200
        assert response.json() == {"text": "transcribed: /tmp/example.wav"}
    finally:
        manager.terminate_all(timeout=1.5)
