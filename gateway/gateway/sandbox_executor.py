from __future__ import annotations

from dataclasses import dataclass

from gateway.sandbox_capability import SandboxCapabilities


@dataclass(frozen=True)
class SandboxSpawnPlan:
    profile: str
    require_rlimit_core: bool
    require_rlimit_nofile: bool
    require_seccomp: bool


def build_sandbox_spawn_plan(
    profile: str | None,
    *,
    capabilities: SandboxCapabilities,
) -> SandboxSpawnPlan | None:
    if profile in (None, "none"):
        return None
    if profile not in {"restricted", "strict"}:
        raise ValueError(
            f"worker_sandbox_profile_unknown: unsupported profile '{profile}'"
        )

    required = {"supports_posix_preexec", "supports_rlimit_core"}
    require_rlimit_nofile = profile == "strict"
    require_seccomp = profile == "strict"
    if require_rlimit_nofile:
        required.add("supports_rlimit_nofile")
    if require_seccomp:
        required.add("supports_seccomp")

    missing = sorted(
        field for field in required if getattr(capabilities, field) is not True
    )
    if missing:
        raise ValueError(
            "worker_sandbox_capability_missing: "
            f"profile '{profile}' requires {', '.join(missing)}"
        )

    return SandboxSpawnPlan(
        profile=profile,
        require_rlimit_core=True,
        require_rlimit_nofile=require_rlimit_nofile,
        require_seccomp=require_seccomp,
    )
