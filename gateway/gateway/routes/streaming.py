from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse


def create_streaming_router() -> APIRouter:
    router = APIRouter(prefix="/api/system", tags=["system"])

    @router.get("/stream-demo")
    def stream_demo() -> StreamingResponse:
        return StreamingResponse(
            _stream_demo_events(),
            media_type="text/event-stream",
        )

    return router


def _stream_demo_events() -> Iterator[str]:
    for chunk in ("chunk-1", "chunk-2", "chunk-3"):
        yield _format_sse_event("chunk", chunk)
    yield _format_sse_event("complete", "done")


def _format_sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"
