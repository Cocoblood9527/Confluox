# Plugin Guide

## Current Plugin Model

The repository now supports two plugin types:

- `type: "api"`: in-process FastAPI route registration (existing plugins remain compatible)
- `type: "worker"`: managed background process startup/registration via `process_manager`

Compatibility notes:

- Existing `api` plugins continue to work without migration changes.
- `worker` currently means managed process start/track/stop only; it does **not** mean process sandbox isolation is already implemented.
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
- `command`: argv array started by the gateway through `process_manager`

Important:

- `permissions` is enforced at startup: policy violations reject worker launch before process spawn.
- enforcement is allowlist-based and is not a full OS sandbox policy engine.
- `worker` plugins do not automatically expose HTTP routes.

## API Trust Policy

`api` plugins are trust-gated during discovery:

- plugins under the repository `plugins/` root are trusted by default
- plugins outside trusted roots are treated as untrusted and rejected by default
- untrusted plugins can be enabled only through explicit startup trust config

Startup trust configuration:

- `--trusted-api-plugin-root` / `CONFLUOX_TRUSTED_API_PLUGIN_ROOTS`: add extra trusted roots
- `--trusted-api-plugin` / `CONFLUOX_TRUSTED_API_PLUGINS`: trust specific plugin names from otherwise untrusted sources

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
- [中文插件指南](../zh-CN/plugin-guide.md)
