# Case Studies

## What This Document Covers

This guide provides 3 practical integration cases so you can quickly choose:

- `api in_process`, `api out_of_process`, or `worker`
- the minimal `manifest.json` shape for each model
- the frontend call path to use

All examples are aligned with what the current repository supports.

## Terminology

- `api in_process`: API plugin runs inside the gateway process
- `api out_of_process`: API plugin runs as a separate process managed and proxied by the gateway
- `worker`: managed background process that does not expose HTTP routes by default
- `permissions`: startup policy declarations validated against the host allowlist
- `sandbox_profile`: lightweight worker hardening profile (for example `restricted`, `strict`)
- `X-Confluox-Plugin-Auth`: host-to-plugin internal auth header for out-of-process API mode

## Case 1: Whisper Local Transcription (`api out_of_process`)

Best fit:

- heavy model dependencies and higher memory usage
- process isolation from the main gateway
- stable HTTP APIs for frontend calls

Recommended manifest:

```json
{
  "type": "api",
  "name": "whisper_app",
  "entry": "entry:setup",
  "execution_mode": "out_of_process",
  "command": ["python3", "-m", "whisper_app.server"]
}
```

Template path: `plugins/examples/whisper_oop_template`

Backend contract (minimal shape):

```python
import os

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException

app = FastAPI()
plugin_prefix = os.environ.get("CONFLUOX_PLUGIN_PREFIX", "/api/whisper_app")
plugin_token = os.environ.get("CONFLUOX_PLUGIN_AUTH_TOKEN", "")


def require_host_auth(
    header_token: str | None = Header(default=None, alias="X-Confluox-Plugin-Auth"),
) -> None:
    if header_token != plugin_token:
        raise HTTPException(status_code=401, detail="invalid host auth")


@app.get("/__confluox/health", dependencies=[Depends(require_host_auth)])
def health() -> dict[str, str]:
    return {"status": "ok"}


router = APIRouter(prefix=plugin_prefix, dependencies=[Depends(require_host_auth)])


@router.post("/transcribe")
def transcribe(payload: dict[str, str]) -> dict[str, str]:
    return {"text": f"transcribed: {payload['audio_path']}"}


app.include_router(router)
```

Frontend call (current client contract):

```ts
const result = await apiPost<{ text: string }>('/api/whisper_app/transcribe', {
  audio_path: selectedPath,
  language: 'zh',
})
```

Important:

- current `apiPost` is JSON-based, not a `FormData` upload channel
- for file uploads, define a dedicated upload path and client handling

## Case 2: Background Indexing Task (`worker`)

Best fit:

- long-running background tasks
- no direct HTTP route exposed by the worker itself
- permission declarations and managed lifecycle required
- local/loopback-only processing

Recommended manifest:

```json
{
  "type": "worker",
  "name": "index_worker",
  "runtime": "python",
  "permissions": {
    "fs": ["read:/tmp"],
    "network": ["loopback"]
  },
  "sandbox_profile": "restricted",
  "command": ["python3", "-m", "index_worker.main"]
}
```

Template path: `plugins/examples/index_worker_template`

Implementation pattern:

- let the worker run scan/index/queue tasks in the background
- add a small `api` plugin that reads worker state for the frontend
- keep subprocess details behind the gateway boundary

## Case 3: Markdown Builder (`api in_process`)

Best fit:

- simple route boundaries
- lightweight dependencies
- fastest integration path

Recommended manifest:

```json
{
  "type": "api",
  "name": "md_builder",
  "entry": "entry:setup"
}
```

Template path: `plugins/examples/md_builder_template`

Backend shape:

```python
from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/md")

    @router.post("/build")
    def build(payload: dict[str, str]) -> dict[str, str]:
        output_path = f"{context.data_dir}/site/index.html"
        return {"status": "ok", "output": output_path}

    context.app.include_router(router)
```

Frontend call:

```ts
await apiPost('/api/md/build', { source_dir: '/path/to/docs' })
```

## Packaging Flow

Build gateway artifacts first:

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

Then build the desktop bundle:

```bash
cargo tauri build
```

Case-doc and template smoke check:

```bash
PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_assets.py -q
PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_templates_runtime.py -q
```

## Related Guides

- [Plugin Guide](plugin-guide.md)
- [Integration Guide](integration-guide.md)
- [中文实例说明](../zh-CN/实例说明.md)
