import json

from gateway.artifact_contract import (
    build_artifact_payload,
    load_artifact_file,
    write_artifact_file,
)


def test_build_artifact_payload_contains_required_fields() -> None:
    payload = build_artifact_payload(
        track="pyinstaller",
        platform="darwin-arm64",
        entry="confluox-gateway/confluox-gateway",
        resources_dir="confluox-gateway",
        version="0.1.0",
        built_at="2026-03-17T00:00:00Z",
    )

    assert payload["track"] == "pyinstaller"
    assert payload["platform"] == "darwin-arm64"
    assert payload["entry"] == "confluox-gateway/confluox-gateway"
    assert payload["resources_dir"] == "confluox-gateway"
    assert payload["version"] == "0.1.0"
    assert payload["built_at"] == "2026-03-17T00:00:00Z"


def test_write_artifact_file_serializes_json(tmp_path) -> None:
    artifact_file = tmp_path / "gateway-artifact.json"
    payload = {
        "track": "nuitka",
        "platform": "darwin-arm64",
        "entry": "gateway/gateway",
        "resources_dir": "gateway",
        "version": "0.1.0",
        "built_at": "2026-03-17T00:00:00Z",
    }

    write_artifact_file(artifact_file, payload)

    assert artifact_file.exists()
    parsed = json.loads(artifact_file.read_text(encoding="utf-8"))
    assert parsed == payload


def test_load_artifact_file_round_trips_payload(tmp_path) -> None:
    artifact_file = tmp_path / "gateway-artifact.json"
    artifact_file.write_text(
        json.dumps(
            {
                "track": "pyinstaller",
                "platform": "darwin-arm64",
                "entry": "confluox-gateway/confluox-gateway",
                "resources_dir": "confluox-gateway",
                "version": "0.1.0",
                "built_at": "2026-03-17T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    payload = load_artifact_file(artifact_file)

    assert payload["track"] == "pyinstaller"
    assert payload["entry"] == "confluox-gateway/confluox-gateway"
