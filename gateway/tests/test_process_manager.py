import json
import os
import sys

import pytest

from gateway.sandbox_capability import SandboxCapabilities
from gateway.process_manager import ProcessManager


def test_terminate_all_stops_managed_process() -> None:
    manager = ProcessManager()
    process = manager.spawn([sys.executable, "-c", "import time; time.sleep(60)"])

    assert process.poll() is None

    manager.terminate_all(timeout=1.5)

    assert process.poll() is not None


def test_spawn_worker_tracks_named_status() -> None:
    manager = ProcessManager()
    process = manager.spawn_worker(
        "worker_example",
        [sys.executable, "-c", "import time; time.sleep(60)"],
    )

    statuses = manager.get_worker_statuses()
    assert [status.name for status in statuses] == ["worker_example"]
    assert statuses[0].pid == process.pid
    assert statuses[0].running is True

    manager.terminate_all(timeout=1.5)
    statuses_after_shutdown = manager.get_worker_statuses()
    assert statuses_after_shutdown[0].running is False


@pytest.mark.skipif(os.name == "nt", reason="worker sandbox profile is POSIX-only")
def test_spawn_worker_restricted_profile_disables_core_dumps(tmp_path) -> None:
    output_path = tmp_path / "limits.json"
    command = [
        sys.executable,
        "-c",
        (
            "import json, resource; "
            f"open({repr(str(output_path))}, 'w', encoding='utf-8').write("
            "json.dumps({'core': list(resource.getrlimit(resource.RLIMIT_CORE))}))"
        ),
    ]
    manager = ProcessManager()
    process = manager.spawn_worker(
        "worker_restricted",
        command,
        sandbox_profile="restricted",
    )
    process.wait(timeout=2.0)
    manager.terminate_all(timeout=1.5)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["core"][0] == 0


def test_spawn_worker_rejects_restrictive_profile_when_capabilities_missing() -> None:
    manager = ProcessManager(
        sandbox_capabilities=SandboxCapabilities(
            platform="linux",
            supports_posix_preexec=False,
            supports_rlimit_core=False,
            supports_rlimit_nofile=False,
            supports_seccomp=False,
            supports_cgroup_v2=False,
            supports_job_object=False,
        )
    )

    with pytest.raises(ValueError, match="worker_sandbox_capability_missing"):
        manager.spawn_worker(
            "worker_restricted",
            [sys.executable, "-c", "import time; time.sleep(60)"],
            sandbox_profile="restricted",
        )


@pytest.mark.skipif(os.name == "nt", reason="worker sandbox profile is POSIX-only")
def test_spawn_worker_rejects_strict_profile_when_seccomp_runtime_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gateway.process_manager._has_seccomp_runtime",
        lambda: False,
        raising=False,
    )
    manager = ProcessManager(
        sandbox_capabilities=SandboxCapabilities(
            platform="linux",
            supports_posix_preexec=True,
            supports_rlimit_core=True,
            supports_rlimit_nofile=True,
            supports_seccomp=True,
            supports_cgroup_v2=False,
            supports_job_object=False,
        )
    )

    try:
        with pytest.raises(ValueError, match="worker_sandbox_not_supported"):
            manager.spawn_worker(
                "worker_strict",
                [sys.executable, "-c", "print('strict')"],
                sandbox_profile="strict",
            )
    finally:
        manager.terminate_all(timeout=1.5)
