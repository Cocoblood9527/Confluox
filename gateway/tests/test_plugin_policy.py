from gateway.plugin_policy import (
    WorkerPermissionPolicy,
    WorkerSandboxProfilePolicy,
    evaluate_worker_permissions,
    evaluate_worker_sandbox_profile,
)


def test_policy_allows_loopback_network_permission() -> None:
    decision = evaluate_worker_permissions(
        {"network": ["loopback"]},
        policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
    )

    assert decision.allowed is True
    assert decision.normalized_permissions == {"network": ["loopback"]}
    assert decision.violations == []


def test_policy_rejects_unknown_permission_namespace() -> None:
    decision = evaluate_worker_permissions(
        {"unknown": ["loopback"]},
        policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
    )

    assert decision.allowed is False
    assert [violation.code for violation in decision.violations] == ["unknown_namespace"]
    assert decision.violations[0].namespace == "unknown"


def test_policy_rejects_invalid_permission_entry_format() -> None:
    decision = evaluate_worker_permissions(
        {"network": ["loopback access"]},
        policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
    )

    assert decision.allowed is False
    assert [violation.code for violation in decision.violations] == ["invalid_entry_format"]
    assert decision.violations[0].entry == "loopback access"


def test_policy_rejects_permission_outside_allowlist() -> None:
    decision = evaluate_worker_permissions(
        {"network": ["internet"]},
        policy=WorkerPermissionPolicy(allowlist={"network": ["loopback"]}),
    )

    assert decision.allowed is False
    assert [violation.code for violation in decision.violations] == ["entry_not_allowed"]
    assert decision.violations[0].namespace == "network"
    assert decision.violations[0].entry == "internet"


def test_policy_allows_restricted_worker_sandbox_profile() -> None:
    decision = evaluate_worker_sandbox_profile(
        "restricted",
        policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted", "strict")),
    )

    assert decision.allowed is True
    assert decision.normalized_profile == "restricted"
    assert decision.violations == []


def test_policy_rejects_invalid_worker_sandbox_profile_format() -> None:
    decision = evaluate_worker_sandbox_profile(
        "Restricted!",
        policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert decision.allowed is False
    assert [violation.code for violation in decision.violations] == ["invalid_profile_format"]
    assert decision.violations[0].profile == "Restricted!"


def test_policy_rejects_worker_sandbox_profile_outside_allowlist() -> None:
    decision = evaluate_worker_sandbox_profile(
        "strict",
        policy=WorkerSandboxProfilePolicy(allowed_profiles=("restricted",)),
    )

    assert decision.allowed is False
    assert [violation.code for violation in decision.violations] == ["profile_not_allowed"]
    assert decision.violations[0].profile == "strict"
