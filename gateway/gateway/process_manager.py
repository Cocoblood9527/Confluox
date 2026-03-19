from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from collections.abc import Callable, Sequence
from typing import Mapping

from gateway.sandbox_capability import SandboxCapabilities, detect_host_sandbox_capabilities
from gateway.sandbox_executor import SandboxSpawnPlan, build_sandbox_spawn_plan


@dataclass(frozen=True)
class WorkerProcessStatus:
    name: str
    pid: int | None
    running: bool


class ProcessManager:
    def __init__(
        self,
        *,
        sandbox_capabilities: SandboxCapabilities | None = None,
    ) -> None:
        self._processes: list[subprocess.Popen[bytes]] = []
        self._workers: dict[str, subprocess.Popen[bytes]] = {}
        self._sandbox_capabilities = (
            detect_host_sandbox_capabilities()
            if sandbox_capabilities is None
            else sandbox_capabilities
        )

    def spawn(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
        preexec_fn: Callable[[], None] | None = None,
    ) -> subprocess.Popen[bytes]:
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            if preexec_fn is not None:
                raise ValueError(
                    "worker_sandbox_not_supported: preexec hooks are unavailable on Windows"
                )
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
            if preexec_fn is not None:
                kwargs["preexec_fn"] = preexec_fn
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
        sandbox_profile: str | None = None,
        sandbox_capabilities: SandboxCapabilities | None = None,
    ) -> subprocess.Popen[bytes]:
        capabilities = (
            self._sandbox_capabilities
            if sandbox_capabilities is None
            else sandbox_capabilities
        )
        sandbox_plan = build_sandbox_spawn_plan(
            sandbox_profile,
            capabilities=capabilities,
        )
        process = self.spawn(
            args,
            env=env,
            cwd=cwd,
            preexec_fn=_build_worker_sandbox_preexec(sandbox_plan),
        )
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


def _build_worker_sandbox_preexec(
    sandbox_plan: SandboxSpawnPlan | None,
) -> Callable[[], None] | None:
    if sandbox_plan is None:
        return None
    if os.name == "nt":
        raise ValueError("worker_sandbox_not_supported: sandbox plan requires POSIX support")
    if sandbox_plan.require_seccomp and not _has_seccomp_runtime():
        raise ValueError(
            "worker_sandbox_not_supported: seccomp runtime is unavailable"
        )

    try:
        import resource
    except ImportError as exc:  # pragma: no cover - platform specific
        raise ValueError(
            "worker_sandbox_not_supported: resource module is unavailable"
        ) from exc

    def _preexec() -> None:
        if sandbox_plan.require_rlimit_core:
            _disable_core_dumps(resource)
        if sandbox_plan.require_rlimit_nofile:
            _cap_open_files(resource, maximum=128)

    return _preexec


def _disable_core_dumps(resource_module) -> None:
    if not hasattr(resource_module, "RLIMIT_CORE"):
        return
    resource_module.setrlimit(resource_module.RLIMIT_CORE, (0, 0))


def _cap_open_files(resource_module, *, maximum: int) -> None:
    if not hasattr(resource_module, "RLIMIT_NOFILE"):
        return

    limit_key = resource_module.RLIMIT_NOFILE
    soft, hard = resource_module.getrlimit(limit_key)
    target_soft = _bounded_limit_value(soft, maximum=maximum, resource_module=resource_module)
    target_hard = _bounded_limit_value(hard, maximum=maximum, resource_module=resource_module)
    if target_soft > target_hard:
        target_soft = target_hard
    resource_module.setrlimit(limit_key, (target_soft, target_hard))


def _bounded_limit_value(current: int, *, maximum: int, resource_module) -> int:
    rlim_infinity = getattr(resource_module, "RLIM_INFINITY", None)
    if current < 0 or (rlim_infinity is not None and current == rlim_infinity):
        return maximum
    return min(current, maximum)


def _has_seccomp_runtime() -> bool:
    try:
        import seccomp  # type: ignore # noqa: F401
    except Exception:
        return False
    return True
