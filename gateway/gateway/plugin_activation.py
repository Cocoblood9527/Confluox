from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Literal


ActivationState = Literal["inactive", "activating", "active", "failed"]


@dataclass(frozen=True)
class PluginActivationStatus:
    state: ActivationState
    error_code: str | None = None
    error_message: str | None = None


class PluginActivationController:
    def __init__(self, *, plugin_names: list[str] | None = None) -> None:
        self._lock = threading.Lock()
        self._statuses: dict[str, PluginActivationStatus] = {}
        self._conditions: dict[str, threading.Condition] = {}
        self.register_plugins(plugin_names or [])

    def register_plugins(self, plugin_names: list[str]) -> None:
        with self._lock:
            for plugin_name in plugin_names:
                self._ensure_plugin_locked(plugin_name)

    def ensure_activated(
        self,
        plugin_name: str,
        activate: Callable[[], None],
    ) -> PluginActivationStatus:
        should_activate = False
        condition: threading.Condition

        with self._lock:
            self._ensure_plugin_locked(plugin_name)
            condition = self._conditions[plugin_name]

            while True:
                status = self._statuses[plugin_name]
                if status.state in ("active", "failed"):
                    return status
                if status.state == "inactive":
                    self._statuses[plugin_name] = PluginActivationStatus(state="activating")
                    should_activate = True
                    break
                condition.wait()

        if should_activate:
            try:
                activate()
            except Exception as err:
                failed = PluginActivationStatus(
                    state="failed",
                    error_code=_extract_error_code(str(err)),
                    error_message=str(err),
                )
                with self._lock:
                    self._statuses[plugin_name] = failed
                    condition.notify_all()
                return failed

            activated = PluginActivationStatus(state="active")
            with self._lock:
                self._statuses[plugin_name] = activated
                condition.notify_all()
            return activated

        # This branch should never be hit because active/failed states return inside the lock.
        return PluginActivationStatus(state="failed", error_code="activation_unreachable")

    def snapshot(self) -> dict[str, PluginActivationStatus]:
        with self._lock:
            return dict(self._statuses)

    def _ensure_plugin_locked(self, plugin_name: str) -> None:
        if plugin_name not in self._statuses:
            self._statuses[plugin_name] = PluginActivationStatus(state="inactive")
        if plugin_name not in self._conditions:
            self._conditions[plugin_name] = threading.Condition(self._lock)


def _extract_error_code(error_message: str) -> str:
    if ":" not in error_message:
        return "activation_failed"
    candidate = error_message.split(":", maxsplit=1)[0].strip()
    if candidate == "":
        return "activation_failed"
    return candidate
