#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${GATEWAY_DIR}/.." && pwd)"
DIST_ROOT="${CONFLUOX_GATEWAY_DIST_ROOT:-${REPO_DIR}/dist/gateway}"
SCAN_REPORT="${CONFLUOX_GATEWAY_SCAN_REPORT:-${GATEWAY_DIR}/build/plugin-scan.json}"

usage() {
  cat <<'EOF'
Usage: ./scripts/build_gateway.sh [--track nuitka|pyinstaller|all] [--prefer nuitka|pyinstaller]

Options:
  --track   Select build track. Default: all
  --prefer  Preferred execution order when --track=all. Default: nuitka
EOF
}

TRACK="all"
PREFER="nuitka"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --track)
      TRACK="${2:-}"
      shift 2
      ;;
    --prefer)
      PREFER="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${TRACK}" in
  nuitka|pyinstaller|all) ;;
  *)
    echo "--track must be one of: nuitka, pyinstaller, all" >&2
    exit 2
    ;;
esac

case "${PREFER}" in
  nuitka|pyinstaller) ;;
  *)
    echo "--prefer must be one of: nuitka, pyinstaller" >&2
    exit 2
    ;;
esac

cd "${GATEWAY_DIR}"
python3 scripts/scan_plugins.py --plugins-dir "${REPO_DIR}/plugins" --out "${SCAN_REPORT}" >/dev/null
mkdir -p "${DIST_ROOT}"
# Remove legacy single-track output path so Tauri resources only contain dual-track layout.
rm -rf "${DIST_ROOT}/confluox-gateway"

declare -a track_order
if [[ "${TRACK}" == "all" ]]; then
  if [[ "${PREFER}" == "pyinstaller" ]]; then
    track_order=("pyinstaller" "nuitka")
  else
    track_order=("nuitka" "pyinstaller")
  fi
else
  track_order=("${TRACK}")
fi

TRACK_STATUS_NUITKA="not-run"
TRACK_STATUS_PYINSTALLER="not-run"
for track in "${track_order[@]}"; do
  echo "[build_gateway] starting track: ${track}"
  if CONFLUOX_GATEWAY_SCAN_REPORT="${SCAN_REPORT}" "${SCRIPT_DIR}/build_gateway_${track}.sh"; then
    if [[ "${track}" == "nuitka" ]]; then
      TRACK_STATUS_NUITKA="ok"
    else
      TRACK_STATUS_PYINSTALLER="ok"
    fi
    echo "[build_gateway] track succeeded: ${track}"
  else
    if [[ "${track}" == "nuitka" ]]; then
      TRACK_STATUS_NUITKA="fail"
    else
      TRACK_STATUS_PYINSTALLER="fail"
    fi
    echo "[build_gateway] track failed: ${track}" >&2
  fi
done

if [[ "${TRACK}" == "all" ]]; then
  if [[ "${TRACK_STATUS_NUITKA}" == "ok" || "${TRACK_STATUS_PYINSTALLER}" == "ok" ]]; then
    echo "[build_gateway] all mode result: success (at least one track succeeded)"
    exit 0
  fi
  echo "[build_gateway] all mode result: failed (both tracks failed)" >&2
  exit 1
fi

if [[ "${TRACK}" == "nuitka" && "${TRACK_STATUS_NUITKA}" == "ok" ]]; then
  exit 0
fi
if [[ "${TRACK}" == "pyinstaller" && "${TRACK_STATUS_PYINSTALLER}" == "ok" ]]; then
  exit 0
fi
exit 1
