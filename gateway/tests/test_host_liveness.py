import asyncio
import os

import pytest

from gateway.host_liveness import is_host_alive, start_host_liveness_watch


def test_current_pid_is_alive() -> None:
    assert is_host_alive(os.getpid()) is True


def test_non_existing_pid_is_not_alive() -> None:
    assert is_host_alive(999_999_999) is False


@pytest.mark.anyio
async def test_watch_triggers_callback_when_host_exits() -> None:
    state = {"checks": 0, "called": False}

    def fake_alive_check(_host_pid: int) -> bool:
        state["checks"] += 1
        return state["checks"] < 2

    async def on_host_exit() -> None:
        state["called"] = True

    await start_host_liveness_watch(
        host_pid=1234,
        on_host_exit=on_host_exit,
        poll_interval=0.001,
        alive_check=fake_alive_check,
    )

    assert state["called"] is True
