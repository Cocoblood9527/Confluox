import json

import pytest

from gateway.plugin_manifest import PluginManifest, parse_plugin_manifest


def test_parse_valid_legacy_api_manifest() -> None:
    manifest = parse_plugin_manifest(
        {
            "type": "api",
            "entry": "entry:setup",
            "name": "example_api",
        }
    )

    assert isinstance(manifest, PluginManifest)
    assert manifest.type == "api"
    assert manifest.name == "example_api"
    assert manifest.entry == "entry:setup"
    assert manifest.command is None
    assert manifest.execution_mode is None


def test_parse_valid_worker_manifest_with_command() -> None:
    manifest = parse_plugin_manifest(
        {
            "type": "worker",
            "name": "example_worker",
            "command": ["python3", "-m", "worker.main"],
            "runtime": "python",
            "permissions": {"fs": ["read:/tmp"], "network": ["loopback"]},
            "sandbox_profile": "restricted",
        }
    )

    assert manifest.type == "worker"
    assert manifest.command == ["python3", "-m", "worker.main"]
    assert manifest.runtime == "python"
    assert manifest.permissions == {"fs": ["read:/tmp"], "network": ["loopback"]}
    assert manifest.sandbox_profile == "restricted"


def test_permissions_entries_are_left_for_policy_enforcement() -> None:
    manifest = parse_plugin_manifest(
        {
            "type": "worker",
            "name": "worker_with_policy_entries",
            "command": ["python3", "-m", "worker.main"],
            "permissions": {"network": ["loopback access"]},
        }
    )

    assert manifest.permissions == {"network": ["loopback access"]}


def test_rejects_invalid_type() -> None:
    with pytest.raises(ValueError, match="type"):
        parse_plugin_manifest(
            {
                "type": "service",
                "entry": "entry:setup",
                "name": "bad_type",
            }
        )


def test_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError, match="entry"):
        parse_plugin_manifest(
            {
                "type": "api",
                "entry": "entry_without_separator",
                "name": "bad_entry",
            }
        )


def test_rejects_invalid_permissions_schema() -> None:
    with pytest.raises(ValueError, match="permissions"):
        parse_plugin_manifest(
            {
                "type": "worker",
                "name": "bad_permissions",
                "command": ["python3", "-m", "worker.main"],
                "permissions": {"fs": "read:/tmp"},
            }
        )


def test_rejects_non_string_sandbox_profile() -> None:
    with pytest.raises(ValueError, match="sandbox_profile"):
        parse_plugin_manifest(
            {
                "type": "worker",
                "name": "bad_sandbox_profile",
                "command": ["python3", "-m", "worker.main"],
                "sandbox_profile": 123,
            }
        )


def test_rejects_sandbox_profile_on_api_plugin() -> None:
    with pytest.raises(ValueError, match="sandbox_profile"):
        parse_plugin_manifest(
            {
                "type": "api",
                "name": "bad_api_sandbox_profile",
                "entry": "entry:setup",
                "sandbox_profile": "restricted",
            }
        )


def test_accepts_api_execution_mode_when_valid() -> None:
    manifest = parse_plugin_manifest(
        {
            "type": "api",
            "name": "api_out_of_process",
            "entry": "entry:setup",
            "execution_mode": "out_of_process",
        }
    )

    assert manifest.execution_mode == "out_of_process"


def test_rejects_execution_mode_on_worker_plugin() -> None:
    with pytest.raises(ValueError, match="execution_mode"):
        parse_plugin_manifest(
            {
                "type": "worker",
                "name": "bad_worker_execution_mode",
                "command": ["python3", "-m", "worker.main"],
                "execution_mode": "in_process",
            }
        )


def test_rejects_invalid_api_execution_mode_value() -> None:
    with pytest.raises(ValueError, match="execution_mode"):
        parse_plugin_manifest(
            {
                "type": "api",
                "name": "bad_api_execution_mode",
                "entry": "entry:setup",
                "execution_mode": "forked",
            }
        )
