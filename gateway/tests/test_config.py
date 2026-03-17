import pytest

from gateway.config import Config, parse_config


def test_parse_config_from_cli_args() -> None:
    config = parse_config(
        [
            "--data-dir",
            "/tmp/data",
            "--auth-token",
            "secret-token",
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "1234",
            "--allowed-origin",
            "https://app.local",
        ]
    )

    assert isinstance(config, Config)
    assert config.data_dir == "/tmp/data"
    assert config.auth_token == "secret-token"
    assert config.ready_file == "/tmp/gateway.ready.json"
    assert config.host_pid == 1234
    assert config.allowed_origin == "https://app.local"


def test_parse_config_from_env() -> None:
    config = parse_config(
        [],
        env={
            "CONFLUOX_DATA_DIR": "/var/lib/confluox",
            "CONFLUOX_AUTH_TOKEN": "env-token",
            "CONFLUOX_READY_FILE": "/var/lib/confluox/ready.json",
            "CONFLUOX_HOST_PID": "4321",
            "CONFLUOX_ALLOWED_ORIGIN": "tauri://localhost",
        },
    )

    assert config.data_dir == "/var/lib/confluox"
    assert config.auth_token == "env-token"
    assert config.ready_file == "/var/lib/confluox/ready.json"
    assert config.host_pid == 4321
    assert config.allowed_origin == "tauri://localhost"


def test_rejects_wildcard_allowed_origin() -> None:
    with pytest.raises(ValueError, match="allowed_origin"):
        parse_config(
            [
                "--data-dir",
                "/tmp/data",
                "--auth-token",
                "secret-token",
                "--ready-file",
                "/tmp/gateway.ready.json",
                "--host-pid",
                "1234",
                "--allowed-origin",
                "*",
            ]
        )
