from __future__ import annotations

import os

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
import uvicorn


app = FastAPI()
plugin_prefix = os.environ.get("CONFLUOX_PLUGIN_PREFIX", "/api/whisper_app")
plugin_auth_token = os.environ.get("CONFLUOX_PLUGIN_AUTH_TOKEN", "")


def require_host_auth(
    header_token: str | None = Header(default=None, alias="X-Confluox-Plugin-Auth"),
) -> None:
    if header_token != plugin_auth_token:
        raise HTTPException(status_code=401, detail="invalid host auth")


@app.get("/__confluox/health", dependencies=[Depends(require_host_auth)])
def health() -> dict[str, str]:
    return {"status": "ok"}


router = APIRouter(prefix=plugin_prefix, dependencies=[Depends(require_host_auth)])


@router.post("/transcribe")
def transcribe(payload: dict[str, str]) -> dict[str, str]:
    audio_path = payload.get("audio_path", "")
    return {"text": f"transcribed: {audio_path}"}


app.include_router(router)


def setup(context) -> None:
    # out_of_process plugins are started by command and proxied by host.
    # setup is kept for manifest compatibility and copyability.
    return None


def main() -> None:
    port = int(os.environ.get("CONFLUOX_PLUGIN_PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
