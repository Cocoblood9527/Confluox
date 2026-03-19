from __future__ import annotations

from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/md")

    @router.post("/build")
    def build(payload: dict[str, str]) -> dict[str, str]:
        source_dir = payload.get("source_dir", "")
        output_path = f"{context.data_dir}/site/index.html"
        return {"status": "ok", "source_dir": source_dir, "output": output_path}

    context.app.include_router(router)
