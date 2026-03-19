import pytest

from gateway.sandbox_capability import (
    SandboxCapabilities,
    detect_host_sandbox_capabilities,
    normalize_sandbox_capabilities,
)


def test_detect_host_sandbox_capabilities_linux_shape() -> None:
    capabilities = detect_host_sandbox_capabilities(
        platform_name="linux",
        has_resource_module=True,
        has_seccomp_module=False,
        cgroup_v2_available=True,
    )

    assert isinstance(capabilities, SandboxCapabilities)
    assert capabilities.platform == "linux"
    assert capabilities.supports_posix_preexec is True
    assert capabilities.supports_rlimit_core is True
    assert capabilities.supports_rlimit_nofile is True
    assert capabilities.supports_seccomp is False
    assert capabilities.supports_cgroup_v2 is True
    assert capabilities.supports_job_object is False


def test_detect_host_sandbox_capabilities_unsupported_platform_is_explicit() -> None:
    capabilities = detect_host_sandbox_capabilities(
        platform_name="plan9",
        has_resource_module=False,
    )

    assert capabilities.platform == "plan9"
    assert capabilities.supports_posix_preexec is False
    assert capabilities.supports_rlimit_core is False
    assert capabilities.supports_rlimit_nofile is False
    assert capabilities.supports_seccomp is False
    assert capabilities.supports_cgroup_v2 is False
    assert capabilities.supports_job_object is False


def test_normalize_sandbox_capabilities_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="supports_posix_preexec"):
        normalize_sandbox_capabilities(
            {
                "platform": "linux",
                "supports_posix_preexec": "yes",
                "supports_rlimit_core": True,
                "supports_rlimit_nofile": True,
                "supports_seccomp": False,
                "supports_cgroup_v2": False,
                "supports_job_object": False,
            }
        )


def test_normalize_sandbox_capabilities_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="unknown fields"):
        normalize_sandbox_capabilities(
            {
                "platform": "linux",
                "supports_posix_preexec": True,
                "supports_rlimit_core": True,
                "supports_rlimit_nofile": True,
                "supports_seccomp": False,
                "supports_cgroup_v2": False,
                "supports_job_object": False,
                "supports_extra_feature": True,
            }
        )
