# Confluox v0.2.3: Phase 2 Hardening Complete

Release date: 2026-03-19
Tag: `v0.2.3-phase2-hardening-complete`

## Highlights

- Completed the full Phase 2 hardening slice tracked by issues `#4`, `#5`, and `#6`.
- Worker startup now includes policy enforcement plus lightweight OS-level sandbox hardening hooks.
- API plugins now support out-of-process execution with health/auth/proxy contracts and resilience controls.

## What Landed In This Phase

### 1. Worker Sandbox Profile Policy + Runtime Gate

- Added typed `sandbox_profile` model and policy decisions for worker manifests.
- Enforced sandbox profile checks before worker process spawn.
- Added structured rejection diagnostics for policy violations.

### 2. API Out-of-Process Execution Path

- Added `execution_mode` contract for API plugins.
- Implemented out-of-process plugin activation flow:
  - process spawn
  - health-check handshake
  - auth token injection and verification
  - route proxying under `/api/<plugin_name>`
- Added diagnostics for timeout/crash/auth failure and upstream unavailability.

### 3. Runtime Channel Hardening And Guardrails

- Added activation quota controls and circuit-breaker behavior for out-of-process API plugins.
- Added explicit error codes for quota/circuit/auth/runtime failures.

### 4. Final #4 Delivery Slice (OS-Level Worker Hardening Hooks)

- Added process-level OS hardening hooks in worker spawn path on POSIX:
  - `sandbox_profile=restricted` -> `RLIMIT_CORE=0`
  - `sandbox_profile=strict` -> `RLIMIT_CORE=0` + capped `RLIMIT_NOFILE`
- Added structured runtime rejection path when host sandbox runtime is not supported.
- Updated plugin guides in English and Chinese with compatibility and boundary notes.

## Verification Snapshot

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q` -> `84 passed`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture` -> `8 passed, 0 failed`
- `cd frontend && npm run build` -> build succeeded

## Scope Boundaries

This release does not add:

- Full kernel-level worker sandboxing (`seccomp`/`cgroup` policy engine)
- Streaming/WebSocket/reconnect protocol changes

## Related Tracking

- `#4`: https://github.com/Cocoblood9527/Confluox/issues/4
- `#5`: https://github.com/Cocoblood9527/Confluox/issues/5
- `#6`: https://github.com/Cocoblood9527/Confluox/issues/6
