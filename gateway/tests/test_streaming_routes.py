from fastapi.testclient import TestClient

from gateway.main import create_app


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer secret-token"}


def test_stream_demo_accepts_valid_bearer_token() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get("/api/system/stream-demo", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_stream_demo_emits_multiple_chunks_with_sse_framing() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get("/api/system/stream-demo", headers=_auth_headers())

    assert response.status_code == 200
    assert response.text.count("event: chunk") == 3
    assert "data: chunk-1\n\n" in response.text
    assert "data: chunk-2\n\n" in response.text
    assert "data: chunk-3\n\n" in response.text


def test_stream_demo_completes_with_terminal_event() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get("/api/system/stream-demo", headers=_auth_headers())

    assert response.status_code == 200
    assert response.text.endswith("event: complete\ndata: done\n\n")


def test_stream_demo_rejects_unauthorized_access() -> None:
    app = create_app(auth_token="secret-token", allowed_origin="https://app.local")
    client = TestClient(app)

    response = client.get("/api/system/stream-demo")

    assert response.status_code == 401
