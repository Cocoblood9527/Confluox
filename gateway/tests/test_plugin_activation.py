import pytest

from gateway.plugin_activation import PluginActivationController


def test_activation_transitions_from_inactive_to_active() -> None:
    controller = PluginActivationController(plugin_names=["example"])

    before = controller.snapshot()["example"]
    assert before.state == "inactive"
    assert before.error_code is None
    assert before.error_message is None

    seen_states: list[str] = []

    def activate() -> None:
        seen_states.append(controller.snapshot()["example"].state)

    after = controller.ensure_activated("example", activate)

    assert seen_states == ["activating"]
    assert after.state == "active"
    assert after.error_code is None
    assert after.error_message is None


def test_activation_failure_state_is_retained_with_error_code() -> None:
    controller = PluginActivationController(plugin_names=["broken"])
    activate_attempts = 0

    def fail_activation() -> None:
        nonlocal activate_attempts
        activate_attempts += 1
        raise RuntimeError("api_oop_boot_timeout: plugin failed to become healthy")

    first = controller.ensure_activated("broken", fail_activation)
    second = controller.ensure_activated("broken", fail_activation)

    assert activate_attempts == 1
    assert first.state == "failed"
    assert first.error_code == "api_oop_boot_timeout"
    assert "failed to become healthy" in (first.error_message or "")
    assert second.state == "failed"
    assert second.error_code == "api_oop_boot_timeout"


def test_ensure_activated_is_idempotent_for_repeated_calls() -> None:
    controller = PluginActivationController(plugin_names=["idempotent"])
    activate_attempts = 0

    def activate() -> None:
        nonlocal activate_attempts
        activate_attempts += 1

    first = controller.ensure_activated("idempotent", activate)
    second = controller.ensure_activated("idempotent", activate)

    assert activate_attempts == 1
    assert first.state == "active"
    assert second.state == "active"
