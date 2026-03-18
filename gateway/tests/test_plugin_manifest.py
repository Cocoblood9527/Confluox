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


def test_parse_valid_worker_manifest_with_command() -> None:
    manifest = parse_plugin_manifest(
        {
            "type": "worker",
            "name": "example_worker",
            "command": ["python3", "-m", "worker.main"],
            "runtime": "python",
            "permissions": {"fs": ["read:/tmp"], "network": ["loopback"]},
        }
    )

    assert manifest.type == "worker"
    assert manifest.command == ["python3", "-m", "worker.main"]
    assert manifest.runtime == "python"
    assert manifest.permissions == {"fs": ["read:/tmp"], "network": ["loopback"]}


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
