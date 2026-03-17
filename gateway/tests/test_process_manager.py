import sys

from gateway.process_manager import ProcessManager


def test_terminate_all_stops_managed_process() -> None:
    manager = ProcessManager()
    process = manager.spawn([sys.executable, "-c", "import time; time.sleep(60)"])

    assert process.poll() is None

    manager.terminate_all(timeout=1.5)

    assert process.poll() is not None
