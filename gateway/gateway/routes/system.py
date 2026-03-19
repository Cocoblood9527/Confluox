from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request


def create_system_router(on_shutdown: Callable[[], None] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/system", tags=["system"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/shutdown")
    def shutdown() -> dict[str, str]:
        if on_shutdown is not None:
            on_shutdown()
        return {"status": "shutting_down"}

    @router.get("/plugin-activation")
    def plugin_activation(request: Request) -> dict[str, dict[str, dict[str, str | None]]]:
        controller = getattr(request.app.state, "plugin_activation_controller", None)
        if controller is None:
            return {"plugins": {}}
        snapshot = controller.snapshot()
        plugins: dict[str, dict[str, str | None]] = {}
        for name, status in snapshot.items():
            plugins[name] = {
                "state": status.state,
                "error_code": status.error_code,
                "error_message": status.error_message,
            }
        return {"plugins": plugins}

    return router
