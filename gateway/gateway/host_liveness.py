from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
import os
import time
from typing import TextIO


def start_host_liveness_watch(
    *,
    on_host_exit: Callable[[], None | Awaitable[None]],
    stream: TextIO | None = None,
    host_pid: int | None = None,
    poll_interval: float = 1.0,
    is_alive_checker: Callable[[int], bool] | None = None,
    read_size: int = 1,
) -> None:
    if host_pid is not None:
        checker = is_host_alive if is_alive_checker is None else is_alive_checker
        while checker(host_pid):
            time.sleep(poll_interval)
        _invoke_exit_callback(on_host_exit)
        return

    if stream is None:
        raise ValueError("stream is required when host_pid is not provided")

    while True:
        try:
            chunk = stream.read(read_size)
        except Exception:
            chunk = ""
        if chunk == "":
            _invoke_exit_callback(on_host_exit)
            return


def is_host_alive(host_pid: int) -> bool:
    if host_pid <= 0:
        return False
    try:
        os.kill(host_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Windows may raise generic OSError (e.g. WinError 87) for invalid PIDs.
        return False
    return True


def _invoke_exit_callback(on_host_exit: Callable[[], None | Awaitable[None]]) -> None:
    result = on_host_exit()
    if inspect.isawaitable(result):
        asyncio.run(result)
