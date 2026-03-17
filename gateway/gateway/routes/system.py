from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter


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

    return router
