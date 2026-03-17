import json

from fastapi.testclient import TestClient

from gateway.main import (
    bind_localhost_ephemeral_socket,
    build_ready_payload,
    create_app,
    is_ready_payload,
    register_ready_file_startup_hook,
    write_ready_file_atomic,
)


def test_bind_localhost_ephemeral_socket_returns_valid_port() -> None:
    sock, port = bind_localhost_ephemeral_socket()
    try:
        host, bound_port = sock.getsockname()
        assert host == "127.0.0.1"
        assert bound_port == port
        assert 1 <= port <= 65535
    finally:
        sock.close()


def test_write_ready_file_atomic_writes_structured_payload(tmp_path) -> None:
    ready_file = tmp_path / "ready.json"
    payload = build_ready_payload(port=32123, version="0.1.0")

    write_ready_file_atomic(ready_file, payload)

    assert ready_file.exists()
    data = json.loads(ready_file.read_text(encoding="utf-8"))
    assert data["status"] == "ready"
    assert data["port"] == 32123
    assert isinstance(data["pid"], int)
    assert data["version"] == "0.1.0"


def test_status_not_ready_is_not_available() -> None:
    ready_payload = build_ready_payload(port=32123, status="ready")
    error_payload = {"status": "error", "message": "startup failed"}

    assert is_ready_payload(ready_payload) is True
    assert is_ready_payload(error_payload) is False


def test_ready_file_written_only_after_app_startup(tmp_path) -> None:
    ready_file = tmp_path / "ready.json"
    app = create_app()
    register_ready_file_startup_hook(app=app, ready_file=ready_file, port=43123)

    assert not ready_file.exists()

    with TestClient(app):
        assert ready_file.exists()
        payload = json.loads(ready_file.read_text(encoding="utf-8"))
        assert payload["status"] == "ready"
        assert payload["port"] == 43123
