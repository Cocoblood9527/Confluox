# Confluox v0.2.0: Worker Permission Enforcement and API Trust Policy

Release date: 2026-03-19
Tag: `v0.2.0-worker-policy-enforcement`

## Highlights

- Worker plugin `permissions` moved from metadata-only to enforced startup policy.
- Worker startup now applies allowlist checks before process spawn.
- Untrusted `api` plugins are blocked by default.
- API plugin trust can be expanded explicitly through startup configuration.

## What Changed

### 1. Worker Permission Policy Is Now Enforced

- Added policy primitives for parsing, normalizing, and evaluating worker permissions.
- Worker processes are not spawned when declared permissions violate host allowlist policy.
- Rejection reasons are surfaced as structured runtime policy violations.

### 2. API Plugin Trust Defaults to Deny for Untrusted Sources

- API plugin discovery now classifies trust source for each descriptor.
- Plugins under repository `plugins/` remain trusted by default.
- Plugins outside trusted roots are rejected unless explicitly trusted.

### 3. New Trust Configuration Surface

- CLI flag: `--trusted-api-plugin-root` (repeatable)
- CLI flag: `--trusted-api-plugin` (repeatable)
- Environment variable: `CONFLUOX_TRUSTED_API_PLUGIN_ROOTS` (comma-separated)
- Environment variable: `CONFLUOX_TRUSTED_API_PLUGINS` (comma-separated)

## Verification Snapshot

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q` -> `57 passed`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture` -> `8 passed, 0 failed`
- `cd frontend && npm run build` -> build succeeded

## Scope Boundaries

This release does not add:

- OS-level worker sandbox isolation
- syscall/network/file enforcement beyond startup gate policy
- out-of-process execution for API plugins
