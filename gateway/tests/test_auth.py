import time

from fastapi.testclient import TestClient

from gateway.auth import issue_scoped_auth_token
from gateway.main import create_app


def test_health_requires_bearer_token_when_auth_enabled() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get("/api/system/health")

    assert response.status_code == 401


def test_health_accepts_valid_bearer_token() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get(
        "/api/system/health",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_origin() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.options(
        "/api/system/health",
        headers={
            "Origin": "https://app.local",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "https://app.local"


def test_cors_does_not_allow_unconfigured_origin() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.options(
        "/api/system/health",
        headers={
            "Origin": "https://evil.local",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "https://evil.local"


def test_health_accepts_valid_scoped_bearer_token() -> None:
    auth_secret = "secret-token"
    scope = "gateway-api"
    app = create_app(
        auth_token=auth_secret,
        allowed_origin="https://app.local",
        auth_token_scope=scope,
        auth_token_ttl_seconds=300,
        auth_token_issued_at=int(time.time()) - 10,
    )
    client = TestClient(app)
    token = issue_scoped_auth_token(
        auth_secret,
        scope=scope,
        issued_at=int(time.time()),
    )

    response = client.get(
        "/api/system/health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_rejects_expired_scoped_bearer_token_with_stable_code() -> None:
    auth_secret = "secret-token"
    scope = "gateway-api"
    app = create_app(
        auth_token=auth_secret,
        allowed_origin="https://app.local",
        auth_token_scope=scope,
        auth_token_ttl_seconds=60,
        auth_token_issued_at=int(time.time()) - 120,
    )
    client = TestClient(app)
    expired = issue_scoped_auth_token(
        auth_secret,
        scope=scope,
        issued_at=int(time.time()) - 120,
    )

    response = client.get(
        "/api/system/health",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "auth_token_expired"


def test_health_rejects_wrong_scope_scoped_bearer_token_with_stable_code() -> None:
    auth_secret = "secret-token"
    app = create_app(
        auth_token=auth_secret,
        allowed_origin="https://app.local",
        auth_token_scope="gateway-api",
        auth_token_ttl_seconds=300,
        auth_token_issued_at=int(time.time()) - 10,
    )
    client = TestClient(app)
    wrong_scope = issue_scoped_auth_token(
        auth_secret,
        scope="plugin-api",
        issued_at=int(time.time()),
    )

    response = client.get(
        "/api/system/health",
        headers={"Authorization": f"Bearer {wrong_scope}"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "auth_token_scope_mismatch"
