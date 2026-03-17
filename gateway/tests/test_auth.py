from fastapi.testclient import TestClient

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
