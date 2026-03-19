# Plugin Guide

## Current Plugin Model

The repository now supports two plugin types:

- `type: "api"`: in-process FastAPI route registration (existing plugins remain compatible)
- `type: "worker"`: managed background process startup/registration via `process_manager`

Compatibility notes:

- Existing `api` plugins continue to work without migration changes.
- `worker` now includes a minimal OS-level hardening path for supported `sandbox_profile` values on POSIX hosts.
- `api` plugin loading now includes a trust gate: untrusted plugin sources are blocked by default unless explicitly trusted.

## Plugin Folder Layout

```text
plugins/
  your_plugin/
    manifest.json
    entry.py
```

## Manifest

Minimal example:

```json
{
  "type": "api",
  "entry": "entry:setup",
  "name": "your_plugin"
}
```

Common fields for `api` plugins:

- `type`: `api`
- `entry`: module and function in `module:function` format
- `name`: display name for the plugin

Minimal `worker` manifest example:

```json
{
  "type": "worker",
  "name": "example_worker",
  "runtime": "python",
  "permissions": {
    "fs": ["read:/tmp"],
    "network": ["loopback"]
  },
  "command": ["python3", "-m", "worker.main"]
}
```

`worker` field notes:

- `type`: `worker`
- `runtime`: runtime label used as metadata
- `permissions`: enforced startup policy declarations for worker launch
- `sandbox_profile`: optional worker sandbox profile declaration (`restricted`, `strict`, etc.)
- `command`: argv array started by the gateway through `process_manager`

Important:

- `permissions` is enforced at startup: policy violations reject worker launch before process spawn.
- `sandbox_profile` is also enforced before spawn; disallowed profiles are rejected with policy diagnostics.
- `sandbox_profile=restricted` applies a POSIX RLIMIT core-dump block (`RLIMIT_CORE=0`) before exec.
- `sandbox_profile=strict` applies the same core-dump block and additionally caps open files (`RLIMIT_NOFILE`).
- enforcement is allowlist-based plus lightweight OS hardening; it is not a full kernel sandbox policy engine.
- `worker` plugins do not automatically expose HTTP routes.

## API Trust Policy

`api` plugins are trust-gated during discovery:

- plugins under the repository `plugins/` root are trusted by default
- plugins outside trusted roots are treated as untrusted and rejected by default
- untrusted plugins can be enabled only through explicit startup trust config

Startup trust configuration:

- `--trusted-api-plugin-root` / `CONFLUOX_TRUSTED_API_PLUGIN_ROOTS`: add extra trusted roots
- `--trusted-api-plugin` / `CONFLUOX_TRUSTED_API_PLUGINS`: trust specific plugin names from otherwise untrusted sources

## API Execution Mode Policy

`api` manifest can optionally declare `execution_mode`:

- `in_process` (default): current supported mode
- `out_of_process`: policy-contract mode for future isolation path

When `execution_mode` is `out_of_process`, `command` is required in manifest:

- `command`: argv array used to launch the plugin process

Current behavior:

- discovery enforces host allowlist for api execution modes
- activation launches `out_of_process` plugin command and performs health-check handshake
- requests are proxied under `/api/<plugin_name>`
- startup failures return explicit diagnostics (`api_oop_boot_timeout`, `api_oop_process_exited`)
- proxy runtime failures return structured `502` payloads (`api_oop_upstream_unavailable`)

Startup execution mode configuration:

- `--allowed-api-execution-mode` / `CONFLUOX_ALLOWED_API_EXECUTION_MODES`: allowlisted modes for discovery policy
- `--api-out-of-process-boot-timeout-seconds` / `CONFLUOX_API_OOP_BOOT_TIMEOUT_SECONDS`: out-of-process boot timeout

Out-of-process plugin runtime contract:

- host injects `CONFLUOX_PLUGIN_PORT`
- host injects `CONFLUOX_PLUGIN_PREFIX`
- host injects `CONFLUOX_PLUGIN_AUTH_TOKEN`
- plugin must expose `GET /__confluox/health` and return `200` when ready
- plugin should require `X-Confluox-Plugin-Auth` for health and proxied requests

Security and resilience controls:

- `--api-out-of-process-max-active-plugins` / `CONFLUOX_API_OOP_MAX_ACTIVE_PLUGINS`: max simultaneously active out-of-process API plugins
- `--api-out-of-process-circuit-failure-threshold` / `CONFLUOX_API_OOP_CIRCUIT_FAILURE_THRESHOLD`: consecutive failures before opening circuit
- `--api-out-of-process-circuit-open-seconds` / `CONFLUOX_API_OOP_CIRCUIT_OPEN_SECONDS`: circuit-open duration

Additional diagnostics:

- auth handshake rejected: `api_oop_auth_failed`
- activation quota exceeded: `api_oop_quota_exceeded`
- circuit open fallback: `api_oop_circuit_open`

## Entry Function

The entry module should expose a `setup(context)` function.

Example:

```python
from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/your-plugin")

    @router.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    context.app.include_router(router)
```

## What `context` Gives You

The plugin context includes:

- `app`: the FastAPI app instance
- `data_dir`: app data directory provided by the desktop host
- `auth`: bearer token used by the local gateway
- `process_manager`: helper for managing child processes
- `resource_resolver`: helper for locating packaged resources

## Recommended Plugin Rules

- keep routes stable and explicit
- do not depend on the global current working directory
- write plugin data under `context.data_dir`
- use the framework-provided resource resolver for packaged assets
- treat the plugin as a local backend surface, not a second application host
- ensure `worker` processes can terminate cleanly on gateway shutdown

## Frontend Access

The frontend calls plugins through the shared API client.

Example:

```ts
const result = await apiGet('/api/your-plugin/ping')
```

The client automatically resolves the gateway base URL and includes the bearer token in requests.

## Suggested Development Flow

1. Create a plugin folder in `plugins/`
2. Add `manifest.json`
3. Implement `entry.py`
4. Run the frontend and desktop host
5. Call the new route from the frontend
6. Add UI only after the route works

## Related Guides

- [Quick Start](quick-start.md)
- [Integration Guide](integration-guide.md)
- [Case Studies](case-studies.md)
- [中文插件指南](../zh-CN/plugin-guide.md)
