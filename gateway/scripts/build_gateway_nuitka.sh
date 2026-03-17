#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${GATEWAY_DIR}/.." && pwd)"
DIST_ROOT="${CONFLUOX_GATEWAY_DIST_ROOT:-${REPO_DIR}/dist/gateway}"
BUILD_ROOT="${CONFLUOX_GATEWAY_BUILD_ROOT:-${GATEWAY_DIR}/build}"
SCAN_REPORT="${CONFLUOX_GATEWAY_SCAN_REPORT:-${BUILD_ROOT}/plugin-scan.json}"
TRACK_DIR="${DIST_ROOT}/nuitka"
TEST_MODE="${CONFLUOX_GATEWAY_TEST_MODE:-0}"
FAIL_TRACKS="${CONFLUOX_GATEWAY_FAIL_TRACKS:-}"
ARTIFACT_PATH="${TRACK_DIR}/gateway-artifact.json"

contains_failed_track() {
  local current_track="$1"
  local raw="${FAIL_TRACKS// /}"
  [[ -n "${raw}" ]] || return 1

  local item
  IFS=',' read -r -a items <<<"${raw}"
  for item in "${items[@]}"; do
    if [[ "${item}" == "${current_track}" ]]; then
      return 0
    fi
  done
  return 1
}

resolve_platform() {
  if [[ -n "${CONFLUOX_ARTIFACT_PLATFORM:-}" ]]; then
    echo "${CONFLUOX_ARTIFACT_PLATFORM}"
    return 0
  fi
  local os arch
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  echo "${os}-${arch}"
}

resolve_version() {
  python3 - <<'PY' "${GATEWAY_DIR}/pyproject.toml"
from pathlib import Path
import re
import sys

content = Path(sys.argv[1]).read_text(encoding="utf-8")
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    tomllib = None

if tomllib is not None:
    data = tomllib.loads(content)
    print(data["project"]["version"])
    raise SystemExit(0)

match = re.search(r'(?m)^version\\s*=\\s*["\\\']([^"\\\']+)["\\\']\\s*$', content)
if not match:
    raise SystemExit("failed to parse [project].version from pyproject.toml")
print(match.group(1))
PY
}

write_artifact() {
  local entry="$1"
  local resources_dir="$2"
  local built_at="${CONFLUOX_GATEWAY_BUILT_AT:-}"
  if [[ -z "${built_at}" ]]; then
    built_at="$(python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
PY
)"
  fi

  local platform version
  platform="$(resolve_platform)"
  version="$(resolve_version)"

  python3 - <<'PY' "${ARTIFACT_PATH}" "${platform}" "${entry}" "${resources_dir}" "${version}" "${built_at}"
from pathlib import Path
import sys

from gateway.artifact_contract import build_artifact_payload, write_artifact_file

artifact_path = Path(sys.argv[1])
payload = build_artifact_payload(
    track="nuitka",
    platform=sys.argv[2],
    entry=sys.argv[3],
    resources_dir=sys.argv[4],
    version=sys.argv[5],
    built_at=sys.argv[6],
)
write_artifact_file(artifact_path, payload)
PY
}

build_from_test_mode() {
  if contains_failed_track "nuitka"; then
    echo "simulated nuitka failure" >&2
    return 1
  fi

  local fake_bin="${TRACK_DIR}/confluox-gateway.dist/confluox-gateway"
  mkdir -p "$(dirname "${fake_bin}")"
  cat <<'EOF' >"${fake_bin}"
#!/usr/bin/env bash
echo "fake nuitka gateway"
EOF
  chmod +x "${fake_bin}"

  write_artifact "confluox-gateway.dist/confluox-gateway" "confluox-gateway.dist"
}

build_real_nuitka() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "nuitka track is currently supported on macOS only (detected $(uname -s))" >&2
    return 1
  fi

  if ! python3 -m nuitka --version >/dev/null 2>&1; then
    echo "nuitka is not installed. Install it with: python3 -m pip install nuitka" >&2
    return 1
  fi

  mkdir -p "${BUILD_ROOT}"
  rm -rf "${TRACK_DIR}"
  mkdir -p "${TRACK_DIR}"

  local plugin_data_args=()
  while IFS= read -r plugin_dir; do
    [[ -n "${plugin_dir}" ]] || continue
    plugin_data_args+=(--include-data-dir="${plugin_dir}=plugins/$(basename "${plugin_dir}")")
  done < <(python3 - <<'PY' "${SCAN_REPORT}"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
for directory in report.get("data_dirs", []):
    print(directory)
PY
)

  local plugin_hidden_import_args=()
  while IFS= read -r module_name; do
    [[ -n "${module_name}" ]] || continue
    plugin_hidden_import_args+=(--include-module="${module_name}")
  done < <(python3 - <<'PY' "${SCAN_REPORT}"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
for module_name in report.get("hidden_imports", []):
    print(module_name)
PY
)

  local pythonpath="${REPO_DIR}:${GATEWAY_DIR}"
  if [[ -n "${PYTHONPATH:-}" ]]; then
    pythonpath="${pythonpath}:${PYTHONPATH}"
  fi

  PYTHONPATH="${pythonpath}" python3 -m nuitka \
    --standalone \
    --assume-yes-for-downloads \
    --remove-output \
    --output-dir="${TRACK_DIR}" \
    --output-filename=confluox-gateway \
    "${plugin_hidden_import_args[@]}" \
    "${plugin_data_args[@]}" \
    gateway/main.py

  local entry_rel=""
  local resources_dir=""
  if [[ -f "${TRACK_DIR}/confluox-gateway" ]]; then
    entry_rel="confluox-gateway"
    resources_dir="."
  elif [[ -f "${TRACK_DIR}/confluox-gateway.exe" ]]; then
    entry_rel="confluox-gateway.exe"
    resources_dir="."
  else
    local dist_match
    dist_match="$(find "${TRACK_DIR}" -maxdepth 2 -type f -name "confluox-gateway" -path "*.dist/*" | head -n 1)"
    if [[ -z "${dist_match}" ]]; then
      dist_match="$(find "${TRACK_DIR}" -maxdepth 2 -type f -name "confluox-gateway.exe" -path "*.dist/*" | head -n 1)"
    fi
    if [[ -n "${dist_match}" ]]; then
      entry_rel="${dist_match#${TRACK_DIR}/}"
      resources_dir="$(basename "$(dirname "${dist_match}")")"
    else
      echo "nuitka output executable missing under ${TRACK_DIR}" >&2
      return 1
    fi
  fi

  write_artifact "${entry_rel}" "${resources_dir}"
}

cd "${GATEWAY_DIR}"
if [[ ! -f "${SCAN_REPORT}" ]]; then
  python3 scripts/scan_plugins.py --plugins-dir "${REPO_DIR}/plugins" --out "${SCAN_REPORT}" >/dev/null
fi

if [[ "${TEST_MODE}" == "1" ]]; then
  build_from_test_mode
else
  build_real_nuitka
fi
