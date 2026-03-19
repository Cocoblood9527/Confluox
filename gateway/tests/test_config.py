import io
import pytest

from gateway.config import Config, parse_config
from gateway.bootstrap import BootstrapConfig, read_bootstrap_config


def test_parse_config_from_cli_args() -> None:
    config = parse_config(
        [
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "1234",
        ]
    )

    assert isinstance(config, Config)
    assert config.ready_file == "/tmp/gateway.ready.json"
    assert config.host_pid == 1234


def test_parse_config_from_env() -> None:
    config = parse_config(
        [],
        env={
            "CONFLUOX_READY_FILE": "/var/lib/confluox/ready.json",
            "CONFLUOX_HOST_PID": "4321",
        },
    )

    assert config.ready_file == "/var/lib/confluox/ready.json"
    assert config.host_pid == 4321


def test_parse_config_allows_api_execution_mode_from_env_and_cli() -> None:
    config = parse_config(
        [
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "8888",
            "--allowed-api-execution-mode",
            "out_of_process",
        ],
        env={
            "CONFLUOX_ALLOWED_API_EXECUTION_MODES": "in_process",
        },
    )

    assert config.allowed_api_execution_modes == ("in_process", "out_of_process")


def test_parse_config_out_of_process_boot_timeout_defaults() -> None:
    config = parse_config(
        [
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "8888",
        ],
    )

    assert config.api_out_of_process_boot_timeout_seconds == 3.0


def test_parse_config_out_of_process_boot_timeout_from_env_and_cli() -> None:
    config = parse_config(
        [
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "8888",
            "--api-out-of-process-boot-timeout-seconds",
            "1.75",
        ],
        env={
            "CONFLUOX_API_OOP_BOOT_TIMEOUT_SECONDS": "2.5",
        },
    )

    assert config.api_out_of_process_boot_timeout_seconds == 1.75


def test_parse_config_out_of_process_security_and_circuit_settings() -> None:
    config = parse_config(
        [
            "--ready-file",
            "/tmp/gateway.ready.json",
            "--host-pid",
            "9999",
            "--api-out-of-process-max-active-plugins",
            "7",
            "--api-out-of-process-circuit-failure-threshold",
            "4",
            "--api-out-of-process-circuit-open-seconds",
            "12.5",
        ],
        env={
            "CONFLUOX_API_OOP_MAX_ACTIVE_PLUGINS": "5",
            "CONFLUOX_API_OOP_CIRCUIT_FAILURE_THRESHOLD": "3",
            "CONFLUOX_API_OOP_CIRCUIT_OPEN_SECONDS": "9.0",
        },
    )

    assert config.api_out_of_process_max_active_plugins == 7
    assert config.api_out_of_process_circuit_failure_threshold == 4
    assert config.api_out_of_process_circuit_open_seconds == 12.5


def test_parse_bootstrap_from_stdin_json_line() -> None:
    stream = io.StringIO(
        '{"data_dir":"/tmp/data","auth_token":"secret-token","allowed_origin":"https://app.local"}\n'
    )
    bootstrap = read_bootstrap_config(stream)

    assert isinstance(bootstrap, BootstrapConfig)
    assert bootstrap.data_dir == "/tmp/data"
    assert bootstrap.auth_token == "secret-token"
    assert bootstrap.allowed_origin == "https://app.local"


def test_bootstrap_rejects_missing_required_fields() -> None:
    stream = io.StringIO('{"data_dir":"/tmp/data","allowed_origin":"https://app.local"}\n')
    with pytest.raises(ValueError, match="auth_token"):
        read_bootstrap_config(stream)


def test_bootstrap_rejects_malformed_json() -> None:
    stream = io.StringIO("{not-json}\n")
    with pytest.raises(ValueError, match="invalid bootstrap json"):
        read_bootstrap_config(stream)


def test_bootstrap_rejects_blank_payload() -> None:
    stream = io.StringIO("\n")
    with pytest.raises(ValueError, match="bootstrap payload is required"):
        read_bootstrap_config(stream)
