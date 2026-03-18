# Plugin Guide

## Current Plugin Model

The most complete plugin path in the current repository is the API plugin model.

The gateway scans the `plugins/` directory, reads each `manifest.json`, and loads plugins whose manifest `type` is `api`.

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

Fields currently used by the loader:

- `type`: must be `api`
- `entry`: module and function in `module:function` format
- `name`: display name for the plugin

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
