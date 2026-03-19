from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class ScopedTokenClaims:
    scope: str
    issued_at: int


@dataclass(frozen=True)
class ScopedTokenValidationResult:
    ok: bool
    error_code: str | None = None
    claims: ScopedTokenClaims | None = None


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        token: str,
        token_scope: str | None = None,
        token_ttl_seconds: int | None = None,
        token_issued_at: int | None = None,
    ) -> None:
        super().__init__(app)
        self._token = token
        self._token_scope = token_scope
        self._token_ttl_seconds = token_ttl_seconds
        self._token_issued_at = token_issued_at

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        if self._token_scope is not None and self._token_ttl_seconds is not None:
            bearer = _extract_bearer_token(header)
            if bearer is None:
                return JSONResponse(
                    {"detail": "Unauthorized", "error": "auth_token_invalid"},
                    status_code=401,
                )

            if bearer == self._token and self._token_issued_at is not None:
                validation = _validate_scope_and_expiry(
                    claims=ScopedTokenClaims(
                        scope=self._token_scope,
                        issued_at=self._token_issued_at,
                    ),
                    required_scope=self._token_scope,
                    ttl_seconds=self._token_ttl_seconds,
                )
            else:
                validation = validate_scoped_auth_token(
                    bearer,
                    secret=self._token,
                    required_scope=self._token_scope,
                    ttl_seconds=self._token_ttl_seconds,
                )
            if not validation.ok:
                return JSONResponse(
                    {"detail": "Unauthorized", "error": validation.error_code},
                    status_code=401,
                )
            return await call_next(request)

        expected = f"Bearer {self._token}"
        if header != expected:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)


def issue_scoped_auth_token(
    secret: str,
    *,
    scope: str,
    issued_at: int | None = None,
) -> str:
    payload = {
        "scope": scope,
        "issued_at": int(time.time()) if issued_at is None else int(issued_at),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"cx1.{payload_b64}.{signature_b64}"


def validate_scoped_auth_token(
    token: str,
    *,
    secret: str,
    required_scope: str,
    ttl_seconds: int,
    now_seconds: int | None = None,
) -> ScopedTokenValidationResult:
    claims = _decode_scoped_auth_token(token, secret=secret)
    if claims is None:
        return ScopedTokenValidationResult(ok=False, error_code="auth_token_invalid")
    return _validate_scope_and_expiry(
        claims=claims,
        required_scope=required_scope,
        ttl_seconds=ttl_seconds,
        now_seconds=now_seconds,
    )


def _validate_scope_and_expiry(
    *,
    claims: ScopedTokenClaims,
    required_scope: str,
    ttl_seconds: int,
    now_seconds: int | None = None,
) -> ScopedTokenValidationResult:
    if claims.scope != required_scope:
        return ScopedTokenValidationResult(ok=False, error_code="auth_token_scope_mismatch")
    now = int(time.time()) if now_seconds is None else int(now_seconds)
    if now >= claims.issued_at + int(ttl_seconds):
        return ScopedTokenValidationResult(ok=False, error_code="auth_token_expired")
    return ScopedTokenValidationResult(ok=True, claims=claims)


def _decode_scoped_auth_token(token: str, *, secret: str) -> ScopedTokenClaims | None:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "cx1":
        return None
    payload_b64 = parts[1]
    signature_b64 = parts[2]
    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected)
    if not hmac.compare_digest(expected_b64, signature_b64):
        return None
    payload_raw = _b64url_decode(payload_b64)
    if payload_raw is None:
        return None
    try:
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    scope = payload.get("scope")
    issued_at = payload.get("issued_at")
    if not isinstance(scope, str) or scope == "":
        return None
    if not isinstance(issued_at, int):
        return None
    return ScopedTokenClaims(scope=scope, issued_at=issued_at)


def _extract_bearer_token(header: str) -> str | None:
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer ") :].strip()
    if token == "":
        return None
    return token


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes | None:
    pad = "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.urlsafe_b64decode((value + pad).encode("ascii"))
    except Exception:
        return None
