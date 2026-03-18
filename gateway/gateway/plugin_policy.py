from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence


_ENTRY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:/-]*$")


@dataclass(frozen=True)
class PermissionPolicyViolation:
    code: str
    namespace: str
    entry: str | None
    message: str


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    normalized_permissions: dict[str, list[str]]
    violations: list[PermissionPolicyViolation]


@dataclass(frozen=True)
class WorkerPermissionPolicy:
    allowlist: Mapping[str, Sequence[str]]


def normalize_permission_declarations(
    permissions: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    return _normalize_permission_map(permissions, subject="permissions")


def normalize_permission_allowlist(
    allowlist: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    return _normalize_permission_map(allowlist, subject="allowlist")


def evaluate_worker_permissions(
    permissions: Mapping[str, Sequence[str]],
    *,
    policy: WorkerPermissionPolicy,
) -> PermissionDecision:
    normalized_permissions = normalize_permission_declarations(permissions)
    normalized_allowlist = normalize_permission_allowlist(policy.allowlist)

    violations: list[PermissionPolicyViolation] = []
    for namespace, entries in normalized_permissions.items():
        allowed_entries = normalized_allowlist.get(namespace)
        if allowed_entries is None:
            violations.append(
                PermissionPolicyViolation(
                    code="unknown_namespace",
                    namespace=namespace,
                    entry=None,
                    message=f"permission namespace '{namespace}' is not allowed",
                )
            )
            continue

        allowed_entry_set = set(allowed_entries)
        for entry in entries:
            if _ENTRY_PATTERN.fullmatch(entry) is None:
                violations.append(
                    PermissionPolicyViolation(
                        code="invalid_entry_format",
                        namespace=namespace,
                        entry=entry,
                        message=(
                            "permission entry must match "
                            "'^[a-z0-9][a-z0-9._:/-]*$'"
                        ),
                    )
                )
                continue

            if entry not in allowed_entry_set:
                violations.append(
                    PermissionPolicyViolation(
                        code="entry_not_allowed",
                        namespace=namespace,
                        entry=entry,
                        message=(
                            f"permission entry '{entry}' is not in allowlist for "
                            f"namespace '{namespace}'"
                        ),
                    )
                )

    return PermissionDecision(
        allowed=len(violations) == 0,
        normalized_permissions=normalized_permissions,
        violations=violations,
    )


def _normalize_permission_map(
    raw: Mapping[str, Sequence[str]],
    *,
    subject: str,
) -> dict[str, list[str]]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{subject} must be an object")

    normalized: dict[str, list[str]] = {}
    for namespace, entries_raw in raw.items():
        if not isinstance(namespace, str) or namespace == "":
            raise ValueError(f"{subject} keys must be non-empty strings")
        if isinstance(entries_raw, (str, bytes)) or not isinstance(entries_raw, Sequence):
            raise ValueError(f"{subject} values must be arrays of strings")

        entries: list[str] = []
        for entry in entries_raw:
            if not isinstance(entry, str) or entry.strip() == "":
                raise ValueError(f"{subject} values must be arrays of non-empty strings")
            if entry not in entries:
                entries.append(entry)
        normalized[namespace] = entries
    return normalized
