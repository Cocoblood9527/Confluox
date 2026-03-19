from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class SandboxCapabilities:
    platform: str
    supports_posix_preexec: bool
    supports_rlimit_core: bool
    supports_rlimit_nofile: bool
    supports_seccomp: bool
    supports_cgroup_v2: bool
    supports_job_object: bool


def normalize_sandbox_capabilities(raw: Mapping[str, object]) -> SandboxCapabilities:
    expected_fields = {
        "platform",
        "supports_posix_preexec",
        "supports_rlimit_core",
        "supports_rlimit_nofile",
        "supports_seccomp",
        "supports_cgroup_v2",
        "supports_job_object",
    }
    unknown_fields = sorted(set(raw.keys()) - expected_fields)
    if unknown_fields:
        raise ValueError(f"unknown fields in sandbox capabilities: {', '.join(unknown_fields)}")

    platform = raw.get("platform")
    if not isinstance(platform, str) or platform == "":
        raise ValueError("platform must be non-empty string")

    boolean_fields = (
        "supports_posix_preexec",
        "supports_rlimit_core",
        "supports_rlimit_nofile",
        "supports_seccomp",
        "supports_cgroup_v2",
        "supports_job_object",
    )
    normalized: dict[str, bool] = {}
    for field in boolean_fields:
        value = raw.get(field)
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be boolean")
        normalized[field] = value

    return SandboxCapabilities(
        platform=platform,
        supports_posix_preexec=normalized["supports_posix_preexec"],
        supports_rlimit_core=normalized["supports_rlimit_core"],
        supports_rlimit_nofile=normalized["supports_rlimit_nofile"],
        supports_seccomp=normalized["supports_seccomp"],
        supports_cgroup_v2=normalized["supports_cgroup_v2"],
        supports_job_object=normalized["supports_job_object"],
    )


def detect_host_sandbox_capabilities(
    *,
    platform_name: str | None = None,
    has_resource_module: bool | None = None,
    has_seccomp_module: bool | None = None,
    cgroup_v2_available: bool | None = None,
) -> SandboxCapabilities:
    resolved_platform = _resolve_platform_name(platform_name)
    is_windows = resolved_platform.startswith("win")
    supports_posix_preexec = _supports_posix_preexec(resolved_platform)

    resource_supported = (
        _has_resource_module() if has_resource_module is None else has_resource_module
    )
    seccomp_supported = (
        _has_seccomp_module() if has_seccomp_module is None else has_seccomp_module
    )
    cgroup_supported = (
        _has_cgroup_v2() if cgroup_v2_available is None else cgroup_v2_available
    )

    return normalize_sandbox_capabilities(
        {
            "platform": resolved_platform,
            "supports_posix_preexec": supports_posix_preexec,
            "supports_rlimit_core": supports_posix_preexec and resource_supported,
            "supports_rlimit_nofile": supports_posix_preexec and resource_supported,
            "supports_seccomp": resolved_platform.startswith("linux") and seccomp_supported,
            "supports_cgroup_v2": resolved_platform.startswith("linux") and cgroup_supported,
            "supports_job_object": is_windows,
        }
    )


def _resolve_platform_name(platform_name: str | None) -> str:
    candidate = sys.platform if platform_name is None else platform_name
    return candidate.strip().lower()


def _supports_posix_preexec(platform_name: str) -> bool:
    return platform_name.startswith(("linux", "darwin", "freebsd", "openbsd", "netbsd"))


def _has_resource_module() -> bool:
    try:
        import resource  # noqa: F401
    except ImportError:
        return False
    return True


def _has_seccomp_module() -> bool:
    try:
        import seccomp  # type: ignore # noqa: F401
    except Exception:
        return False
    return True


def _has_cgroup_v2() -> bool:
    return Path("/sys/fs/cgroup/cgroup.controllers").exists()
