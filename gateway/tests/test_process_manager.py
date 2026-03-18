import sys

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
