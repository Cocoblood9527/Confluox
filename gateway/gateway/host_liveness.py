from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import Awaitable, Callable


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
        return False
    return True


async def start_host_liveness_watch(
    *,
    host_pid: int,
    on_host_exit: Callable[[], None | Awaitable[None]],
    poll_interval: float = 1.0,
    alive_check: Callable[[int], bool] = is_host_alive,
) -> None:
    while True:
        if not alive_check(host_pid):
            result = on_host_exit()
            if inspect.isawaitable(result):
                await result
            return
        await asyncio.sleep(poll_interval)
