#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan plugin manifests for packaging")
    parser.add_argument(
        "--plugins-dir",
        default=str(Path(__file__).resolve().parents[2] / "plugins"),
        help="Path to plugins directory",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "build" / "plugin-scan.json"),
        help="Output JSON report path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plugins_dir = Path(args.plugins_dir).resolve()
    output_path = Path(args.out).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "plugins_dir": str(plugins_dir),
        "hidden_imports": [],
        "data_dirs": [],
        "plugins": [],
    }

    hidden_imports: list[str] = []
    data_dirs: list[str] = []
    plugins: list[dict[str, str]] = []

    if plugins_dir.exists():
        for plugin_dir in sorted(plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue

            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = str(manifest.get("entry", ""))
            module_name = entry.split(":", maxsplit=1)[0] if ":" in entry else ""

            if module_name:
                hidden_imports.append(f"plugins.{plugin_dir.name}.{module_name}")
            data_dirs.append(str(plugin_dir))
            plugins.append(
                {
                    "name": str(manifest.get("name", plugin_dir.name)),
                    "type": str(manifest.get("type", "unknown")),
                    "entry": entry,
                    "path": str(plugin_dir),
                }
            )

    report["hidden_imports"] = hidden_imports
    report["data_dirs"] = data_dirs
    report["plugins"] = plugins

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"plugin scan report written to {output_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
