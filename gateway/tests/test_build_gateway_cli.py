from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _repo_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_script() -> Path:
    return _repo_dir() / "gateway" / "scripts" / "build_gateway.sh"


def _run_build(
    tmp_path: Path,
    *args: str,
    fail_tracks: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CONFLUOX_GATEWAY_TEST_MODE"] = "1"
    env["CONFLUOX_GATEWAY_DIST_ROOT"] = str(tmp_path / "dist" / "gateway")
    env["CONFLUOX_GATEWAY_SCAN_REPORT"] = str(tmp_path / "build" / "plugin-scan.json")
    env["CONFLUOX_GATEWAY_BUILD_ROOT"] = str(tmp_path / "build")
    if fail_tracks:
        env["CONFLUOX_GATEWAY_FAIL_TRACKS"] = fail_tracks

    return subprocess.run(
        ["bash", str(_build_script()), *args],
        cwd=_repo_dir() / "gateway",
        check=False,
        text=True,
        capture_output=True,
        timeout=20,
        env=env,
    )


def _artifact_json(tmp_path: Path, track: str) -> dict[str, str]:
    artifact_path = tmp_path / "dist" / "gateway" / track / "gateway-artifact.json"
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def test_pyinstaller_track_writes_artifact_file(tmp_path) -> None:
    result = _run_build(tmp_path, "--track", "pyinstaller")

    assert result.returncode == 0, result.stderr
    payload = _artifact_json(tmp_path, "pyinstaller")
    assert payload["track"] == "pyinstaller"


def test_nuitka_track_writes_artifact_file(tmp_path) -> None:
    result = _run_build(tmp_path, "--track", "nuitka")

    assert result.returncode == 0, result.stderr
    payload = _artifact_json(tmp_path, "nuitka")
    assert payload["track"] == "nuitka"


def test_track_all_succeeds_when_one_track_passes(tmp_path) -> None:
    result = _run_build(tmp_path, "--track", "all", fail_tracks="nuitka")

    assert result.returncode == 0
    payload = _artifact_json(tmp_path, "pyinstaller")
    assert payload["track"] == "pyinstaller"


def test_track_nuitka_fails_when_nuitka_fails(tmp_path) -> None:
    result = _run_build(tmp_path, "--track", "nuitka", fail_tracks="nuitka")

    assert result.returncode != 0


def test_prefer_flag_controls_execution_order_only(tmp_path) -> None:
    result = _run_build(tmp_path, "--track", "all", "--prefer", "pyinstaller")

    assert result.returncode == 0, result.stderr
    start_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("[build_gateway] starting track:")
    ]
    assert start_lines == [
        "[build_gateway] starting track: pyinstaller",
        "[build_gateway] starting track: nuitka",
    ]
