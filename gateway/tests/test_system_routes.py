from fastapi.testclient import TestClient

from gateway.main import create_app


def test_health_route_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/system/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_shutdown_route_triggers_callback() -> None:
    callback_state = {"called": False}

    def on_shutdown() -> None:
        callback_state["called"] = True

    app = create_app(on_shutdown=on_shutdown)
    client = TestClient(app)

    response = client.post("/api/system/shutdown")

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
    assert callback_state["called"] is True
