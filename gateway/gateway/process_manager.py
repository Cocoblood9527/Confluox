from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Sequence


class ProcessManager:
    def __init__(self) -> None:
        self._processes: list[subprocess.Popen[bytes]] = []

    def spawn(self, args: Sequence[str]) -> subprocess.Popen[bytes]:
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        process = subprocess.Popen(list(args), **kwargs)
        self._processes.append(process)
        return process

    def register(self, process: subprocess.Popen[bytes]) -> None:
        self._processes.append(process)

    def terminate_all(self, timeout: float = 3.0) -> None:
        for process in self._processes:
            if process.poll() is not None:
                continue
            self._terminate(process)

        for process in self._processes:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill(process)

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        if os.name == "nt":
            process.terminate()
            return

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    def _kill(self, process: subprocess.Popen[bytes]) -> None:
        if os.name == "nt":
            process.kill()
            return

        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
