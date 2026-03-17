from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

REQUIRED_FIELDS = (
    "track",
    "platform",
    "entry",
    "resources_dir",
    "version",
    "built_at",
)
VALID_TRACKS = {"nuitka", "pyinstaller"}


def build_artifact_payload(
    *,
    track: str,
    platform: str,
    entry: str,
    resources_dir: str,
    version: str,
    built_at: str,
) -> dict[str, str]:
    payload = {
        "track": track,
        "platform": platform,
        "entry": entry,
        "resources_dir": resources_dir,
        "version": version,
        "built_at": built_at,
    }
    _validate_payload(payload)
    return payload


def write_artifact_file(path: Path, payload: Mapping[str, str]) -> None:
    serialized = dict(payload)
    _validate_payload(serialized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_artifact_file(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    parsed: Any = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("artifact payload must be a JSON object")
    payload = {str(key): value for key, value in parsed.items()}
    _validate_payload(payload)
    return {key: str(value) for key, value in payload.items()}


def _validate_payload(payload: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"artifact payload missing required fields: {', '.join(missing)}")

    for field in REQUIRED_FIELDS:
        value = payload[field]
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"artifact payload field '{field}' must be a non-empty string")

    track = payload["track"]
    if track not in VALID_TRACKS:
        raise ValueError(
            f"artifact payload field 'track' must be one of: {', '.join(sorted(VALID_TRACKS))}"
        )
