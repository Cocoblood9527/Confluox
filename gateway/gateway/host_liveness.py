from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import TextIO


def start_host_liveness_watch(
    *,
    stream: TextIO,
    on_host_exit: Callable[[], None | Awaitable[None]],
    read_size: int = 1,
) -> None:
    while True:
        try:
            chunk = stream.read(read_size)
        except Exception:
            chunk = ""
        if chunk == "":
            _invoke_exit_callback(on_host_exit)
            return


def _invoke_exit_callback(on_host_exit: Callable[[], None | Awaitable[None]]) -> None:
    result = on_host_exit()
    if inspect.isawaitable(result):
        asyncio.run(result)
