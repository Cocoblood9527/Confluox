from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Mapping


@dataclass(frozen=True)
class WorkerProcessStatus:
    name: str
    pid: int | None
    running: bool


class ProcessManager:
    def __init__(self) -> None:
        self._processes: list[subprocess.Popen[bytes]] = []
        self._workers: dict[str, subprocess.Popen[bytes]] = {}

    def spawn(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> subprocess.Popen[bytes]:
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        if env is not None:
            kwargs["env"] = dict(env)
        if cwd is not None:
            kwargs["cwd"] = cwd

        process = subprocess.Popen(list(args), **kwargs)
        self._processes.append(process)
        return process

    def register(self, process: subprocess.Popen[bytes]) -> None:
        if process not in self._processes:
            self._processes.append(process)

    def spawn_worker(
        self,
        name: str,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> subprocess.Popen[bytes]:
        process = self.spawn(args, env=env, cwd=cwd)
        self._workers[name] = process
        return process

    def register_worker(self, name: str, process: subprocess.Popen[bytes]) -> None:
        self.register(process)
        self._workers[name] = process

    def get_worker_statuses(self) -> list[WorkerProcessStatus]:
        statuses: list[WorkerProcessStatus] = []
        for name in sorted(self._workers.keys()):
            process = self._workers[name]
            statuses.append(
                WorkerProcessStatus(
                    name=name,
                    pid=process.pid,
                    running=process.poll() is None,
                )
            )
        return statuses

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
