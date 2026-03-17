from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        expected = f"Bearer {self._token}"
        if header != expected:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)
