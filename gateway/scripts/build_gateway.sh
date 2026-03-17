#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${GATEWAY_DIR}/.." && pwd)"
SCAN_REPORT="${GATEWAY_DIR}/build/plugin-scan.json"

cd "${GATEWAY_DIR}"
python3 scripts/scan_plugins.py --plugins-dir "${REPO_DIR}/plugins" --out "${SCAN_REPORT}"

PLUGIN_DATA_ARGS=()
while IFS= read -r plugin_dir; do
  [[ -n "${plugin_dir}" ]] || continue
  PLUGIN_DATA_ARGS+=(--add-data "${plugin_dir}:plugins/$(basename "${plugin_dir}")")
done < <(python3 - <<'PY' "${SCAN_REPORT}"
import json
import sys

report_path = sys.argv[1]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)
for directory in report.get("data_dirs", []):
    print(directory)
PY
)

pyinstaller \
  --noconfirm \
  --clean \
  --name confluox-gateway \
  --distpath "${REPO_DIR}/dist/gateway" \
  --workpath "${GATEWAY_DIR}/build/pyinstaller" \
  --specpath "${GATEWAY_DIR}/build" \
  --paths "${GATEWAY_DIR}" \
  "${PLUGIN_DATA_ARGS[@]}" \
  gateway/main.py
