# Confluox

[中文说明](README.zh-CN.md)

Confluox is a desktop bridge framework for turning local capabilities into a desktop product with a consistent host, gateway, and plugin model.

It combines:

- `Tauri + Rust` as the desktop host
- `Python + FastAPI` as the local gateway
- `React + Vite` as the frontend shell
- `plugins/` as the main extension surface

## Who Is This For

Confluox is designed for teams that want to:

- package Python capabilities behind a desktop UI
- turn local tools, scripts, or lightweight services into a desktop app
- adapt open-source projects into a managed desktop host
- keep startup, shutdown, auth, and packaging behavior consistent

## Who Is This Not For

Confluox is probably not the right fit if you need:

- zero-modification desktop wrapping for any large open-source system
- a cloud orchestration platform instead of a local desktop host
- a framework that immediately replaces your entire existing application runtime

## Architecture At A Glance

```text
React + Vite frontend
        |
        | invoke + fetch
        v
Tauri desktop host
        |
        | starts / stops / injects runtime config
        v
Python local gateway
        |
        | mounts routes / manages auth / lifecycle
        v
API plugins / adapters / managed local processes
```

Current implementation highlights:

- the desktop host starts the gateway and waits for a structured ready file
- the gateway binds a localhost port, enables bearer-token auth, and loads API plugins
- the frontend gets gateway connection info from Tauri and calls the local API through a shared client
- plugins sit behind the gateway so the desktop host and frontend keep one consistent integration surface

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- Rust toolchain
- Tauri CLI

### Install Dependencies

```bash
python -m pip install -U pip
python -m pip install -e gateway[dev]
cd frontend && npm ci
cargo install tauri-cli --version "^2" --locked
```

### Start Local Development

In terminal 1:

```bash
cd frontend
npm run dev
```

In terminal 2:

```bash
cargo tauri dev
```

The frontend dev server is configured for `http://localhost:1420`, and the desktop host uses that URL in development.

## Repository Structure

```text
frontend/     React + Vite frontend
gateway/      Python gateway and build scripts
src-tauri/    Tauri desktop host
plugins/      Plugin entrypoints and manifests
dist/         Packaged gateway artifacts used for desktop bundling
docs/         Design docs and user-facing guides
```

## Build Your First Plugin

The easiest path today is an API plugin.

Create a new plugin folder:

```text
plugins/
  todo_api/
    manifest.json
    entry.py
```

Example `manifest.json`:

```json
{
  "type": "api",
  "entry": "entry:setup",
  "name": "todo_api"
}
```

Example `entry.py`:

```python
from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/todo")

    @router.get("/items")
    def list_items() -> dict[str, object]:
        return {"items": [], "data_dir": context.data_dir}

    context.app.include_router(router)
```

Then call it from the frontend through the shared API client:

```ts
const result = await apiGet('/api/todo/items')
```

## Integrating An Open-Source Project

Confluox is best treated as a bridge framework, not a zero-effort desktop wrapper for every project.

- Lightweight FastAPI or router-based projects are the best fit. Wrap them as API plugins.
- CLI tools or local services usually need an adapter layer and managed subprocess handling.
- Large full-stack systems should be isolated behind an adapter or proxy model instead of being forced into the main gateway process.

In short:

- low friction: API plugins
- medium friction: adaptable third-party Python projects
- higher friction: large service-style systems

## Packaging

Development mode starts the gateway from Python directly.

Production mode expects bundled gateway artifacts under `dist/gateway`, which are included in the Tauri bundle resources.

To build gateway artifacts:

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

Then build the desktop app:

```bash
cargo tauri build
```

## Documentation

- [Quick Start](docs/en/quick-start.md)
- [Plugin Guide](docs/en/plugin-guide.md)
- [Integration Guide](docs/en/integration-guide.md)
- [Contributing](CONTRIBUTING.md)
- [中文文档入口](README.zh-CN.md)

## Status

Confluox is currently an early-stage framework. The API plugin path is the most complete flow in the current repository, while broader adapter and service-style integrations are still evolving.

## License

Confluox is available under the [MIT License](LICENSE).
