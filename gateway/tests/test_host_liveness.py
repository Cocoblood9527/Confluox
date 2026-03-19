import os
import threading
import time

from gateway.host_liveness import is_host_alive, start_host_liveness_watch


def test_watch_stays_alive_while_pipe_open() -> None:
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r", encoding="utf-8", buffering=1)
    state = {"called": False}

    def on_host_exit() -> None:
        state["called"] = True

    watcher = threading.Thread(
        target=start_host_liveness_watch,
        kwargs={"stream": stream, "on_host_exit": on_host_exit},
        daemon=True,
    )
    watcher.start()

    time.sleep(0.05)
    assert watcher.is_alive() is True
    assert state["called"] is False

    os.close(write_fd)
    watcher.join(timeout=1.0)
    stream.close()


def test_watch_triggers_callback_on_eof() -> None:
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r", encoding="utf-8", buffering=1)
    state = {"called": False}

    def on_host_exit() -> None:
        state["called"] = True

    watcher = threading.Thread(
        target=start_host_liveness_watch,
        kwargs={"stream": stream, "on_host_exit": on_host_exit},
        daemon=True,
    )
    watcher.start()

    os.close(write_fd)
    watcher.join(timeout=1.0)
    stream.close()

    assert state["called"] is True


def test_watch_invokes_callback_exactly_once() -> None:
    read_fd, write_fd = os.pipe()
    stream = os.fdopen(read_fd, "r", encoding="utf-8", buffering=1)
    state = {"calls": 0}

    def on_host_exit() -> None:
        state["calls"] += 1

    watcher = threading.Thread(
        target=start_host_liveness_watch,
        kwargs={"stream": stream, "on_host_exit": on_host_exit},
        daemon=True,
    )
    watcher.start()

    os.close(write_fd)
    watcher.join(timeout=1.0)
    stream.close()

    assert state["calls"] == 1


def test_is_host_alive_returns_true_for_current_process() -> None:
    assert is_host_alive(os.getpid()) is True


def test_is_host_alive_returns_false_for_missing_process() -> None:
    assert is_host_alive(9_999_999) is False


def test_pid_watch_triggers_callback_when_host_dead() -> None:
    state = {"called": False, "checks": 0}

    def on_host_exit() -> None:
        state["called"] = True

    def checker(_: int) -> bool:
        state["checks"] += 1
        return state["checks"] < 2

    start_host_liveness_watch(
        host_pid=1234,
        on_host_exit=on_host_exit,
        poll_interval=0.0,
        is_alive_checker=checker,
    )

    assert state["called"] is True
