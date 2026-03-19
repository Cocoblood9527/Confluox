import pytest

from gateway.sandbox_capability import SandboxCapabilities
from gateway.sandbox_executor import build_sandbox_spawn_plan


def _capabilities(**overrides) -> SandboxCapabilities:
    payload = {
        "platform": "linux",
        "supports_posix_preexec": True,
        "supports_rlimit_core": True,
        "supports_rlimit_nofile": True,
        "supports_seccomp": False,
        "supports_cgroup_v2": False,
        "supports_job_object": False,
    }
    payload.update(overrides)
    return SandboxCapabilities(**payload)


def test_build_sandbox_spawn_plan_returns_none_for_none_profile() -> None:
    plan = build_sandbox_spawn_plan(
        None,
        capabilities=_capabilities(),
    )

    assert plan is None


def test_build_sandbox_spawn_plan_allows_restricted_when_capabilities_present() -> None:
    plan = build_sandbox_spawn_plan(
        "restricted",
        capabilities=_capabilities(),
    )

    assert plan is not None
    assert plan.profile == "restricted"
    assert plan.require_rlimit_core is True
    assert plan.require_rlimit_nofile is False
    assert plan.require_seccomp is False


def test_build_sandbox_spawn_plan_rejects_strict_when_capabilities_missing() -> None:
    with pytest.raises(ValueError, match="worker_sandbox_capability_missing"):
        build_sandbox_spawn_plan(
            "strict",
            capabilities=_capabilities(supports_rlimit_nofile=False),
        )


def test_build_sandbox_spawn_plan_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="worker_sandbox_profile_unknown"):
        build_sandbox_spawn_plan(
            "ultra",
            capabilities=_capabilities(),
        )
