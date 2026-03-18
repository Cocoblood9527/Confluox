import json
import sys

import pytest

from gateway.plugin_runtime import discover_worker_plugins, start_worker_plugins
from gateway.process_manager import ProcessManager


def test_discover_worker_plugins_reads_command_manifest(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_example"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_example",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "runtime": "python",
                "permissions": {"fs": ["read:/tmp"]},
            }
        ),
        encoding="utf-8",
    )

    descriptors = discover_worker_plugins(plugins_dir)

    assert len(descriptors) == 1
    assert descriptors[0].name == "worker_example"
    assert descriptors[0].command[0] == sys.executable
    assert descriptors[0].runtime == "python"


def test_start_worker_plugins_launches_via_process_manager(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_example"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_example",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
            }
        ),
        encoding="utf-8",
    )

    manager = ProcessManager()
    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(descriptors, process_manager=manager)

    assert [status.name for status in statuses] == ["worker_example"]
    assert statuses[0].running is True
    assert statuses[0].pid is not None

    manager.terminate_all(timeout=1.5)
    after_shutdown = manager.get_worker_statuses()
    assert after_shutdown[0].running is False


def test_discover_worker_plugins_rejects_invalid_manifest(tmp_path) -> None:
    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_invalid"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps({"type": "worker", "name": "worker_invalid"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="command"):
        discover_worker_plugins(plugins_dir)
