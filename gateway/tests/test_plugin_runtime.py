import json
import sys

import pytest

from gateway.plugin_policy import WorkerPermissionPolicy, WorkerSandboxProfilePolicy
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
                "sandbox_profile": "restricted",
            }
        ),
        encoding="utf-8",
    )

    descriptors = discover_worker_plugins(plugins_dir)

    assert len(descriptors) == 1
    assert descriptors[0].name == "worker_example"
    assert descriptors[0].command[0] == sys.executable
    assert descriptors[0].runtime == "python"
    assert descriptors[0].sandbox_profile == "restricted"


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
                "sandbox_profile": "restricted",
            }
        ),
        encoding="utf-8",
    )

    manager = ProcessManager()
    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=manager,
        permission_policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
        sandbox_profile_policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert [status.name for status in statuses] == ["worker_example"]
    assert statuses[0].running is True
    assert statuses[0].pid is not None
    assert statuses[0].rejected is False
    assert statuses[0].policy_violations == []

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


def test_start_worker_plugins_rejects_policy_violations_without_spawn(tmp_path) -> None:
    class RecordingProcessManager:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str]]] = []

        def spawn_worker(
            self,
            name: str,
            args: list[str],
            *,
            sandbox_profile: str | None = None,
        ):
            self.calls.append((name, list(args)))
            raise AssertionError("spawn should not be called for rejected worker")

    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_denied"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_denied",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "permissions": {"network": ["internet"]},
            }
        ),
        encoding="utf-8",
    )

    manager = RecordingProcessManager()
    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=manager,
        permission_policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
    )

    assert len(statuses) == 1
    assert statuses[0].name == "worker_denied"
    assert statuses[0].pid is None
    assert statuses[0].running is False
    assert statuses[0].rejected is True
    assert [violation.code for violation in statuses[0].policy_violations] == ["entry_not_allowed"]
    assert manager.calls == []


def test_start_worker_plugins_rejects_sandbox_profile_without_spawn(tmp_path) -> None:
    class RecordingProcessManager:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str]]] = []

        def spawn_worker(
            self,
            name: str,
            args: list[str],
            *,
            sandbox_profile: str | None = None,
        ):
            self.calls.append((name, list(args)))
            raise AssertionError("spawn should not be called for rejected worker")

    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_denied_by_sandbox"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_denied_by_sandbox",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "sandbox_profile": "strict",
            }
        ),
        encoding="utf-8",
    )

    manager = RecordingProcessManager()
    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=manager,
        sandbox_profile_policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert len(statuses) == 1
    assert statuses[0].name == "worker_denied_by_sandbox"
    assert statuses[0].pid is None
    assert statuses[0].running is False
    assert statuses[0].rejected is True
    assert [violation.code for violation in statuses[0].policy_violations] == ["profile_not_allowed"]
    assert [violation.namespace for violation in statuses[0].policy_violations] == ["sandbox_profile"]
    assert [violation.entry for violation in statuses[0].policy_violations] == ["strict"]
    assert manager.calls == []


def test_start_worker_plugins_passes_sandbox_profile_to_process_manager(tmp_path) -> None:
    class FakeProcess:
        pid = 12345

        def poll(self) -> None:
            return None

    class RecordingProcessManager:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str], str | None]] = []

        def spawn_worker(
            self,
            name: str,
            args: list[str],
            *,
            sandbox_profile: str | None = None,
        ) -> FakeProcess:
            self.calls.append((name, list(args), sandbox_profile))
            return FakeProcess()

    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_sandbox_passthrough"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_sandbox_passthrough",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "sandbox_profile": "restricted",
            }
        ),
        encoding="utf-8",
    )

    manager = RecordingProcessManager()
    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=manager,
        sandbox_profile_policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert len(statuses) == 1
    assert statuses[0].rejected is False
    assert manager.calls == [
        (
            "worker_sandbox_passthrough",
            [sys.executable, "-c", "import time; time.sleep(60)"],
            "restricted",
        )
    ]


def test_start_worker_plugins_reports_sandbox_runtime_not_supported(tmp_path) -> None:
    class RecordingProcessManager:
        def spawn_worker(
            self,
            name: str,
            args: list[str],
            *,
            sandbox_profile: str | None = None,
        ):
            raise ValueError("worker_sandbox_not_supported: sandbox profiles require POSIX support")

    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_runtime_rejected"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_runtime_rejected",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "sandbox_profile": "restricted",
            }
        ),
        encoding="utf-8",
    )

    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=RecordingProcessManager(),
        sandbox_profile_policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert len(statuses) == 1
    assert statuses[0].name == "worker_runtime_rejected"
    assert statuses[0].running is False
    assert statuses[0].rejected is True
    assert statuses[0].pid is None
    assert [violation.code for violation in statuses[0].policy_violations] == [
        "sandbox_runtime_not_supported"
    ]
    assert [violation.namespace for violation in statuses[0].policy_violations] == [
        "sandbox_profile"
    ]
    assert [violation.entry for violation in statuses[0].policy_violations] == ["restricted"]


def test_start_worker_plugins_reports_sandbox_capability_missing(tmp_path) -> None:
    class RecordingProcessManager:
        def spawn_worker(
            self,
            name: str,
            args: list[str],
            *,
            sandbox_profile: str | None = None,
        ):
            raise ValueError(
                "worker_sandbox_capability_missing: profile 'strict' requires supports_rlimit_nofile"
            )

    plugins_dir = tmp_path / "plugins"
    worker_dir = plugins_dir / "worker_capability_missing"
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "manifest.json").write_text(
        json.dumps(
            {
                "type": "worker",
                "name": "worker_capability_missing",
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
                "sandbox_profile": "strict",
            }
        ),
        encoding="utf-8",
    )

    descriptors = discover_worker_plugins(plugins_dir)
    statuses = start_worker_plugins(
        descriptors,
        process_manager=RecordingProcessManager(),
        sandbox_profile_policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted", "strict")),
    )

    assert len(statuses) == 1
    assert statuses[0].name == "worker_capability_missing"
    assert statuses[0].running is False
    assert statuses[0].rejected is True
    assert statuses[0].pid is None
    assert [violation.code for violation in statuses[0].policy_violations] == [
        "sandbox_capability_missing"
    ]
    assert [violation.namespace for violation in statuses[0].policy_violations] == [
        "sandbox_profile"
    ]
    assert [violation.entry for violation in statuses[0].policy_violations] == ["strict"]
