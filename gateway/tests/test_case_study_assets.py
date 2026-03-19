from __future__ import annotations

import json
from pathlib import Path

from gateway.plugin_manifest import parse_plugin_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATHS = (
    REPO_ROOT / "docs/zh-CN/实例说明.md",
    REPO_ROOT / "docs/en/case-studies.md",
)
EXAMPLE_DIRS = (
    REPO_ROOT / "plugins/examples/whisper_oop_template",
    REPO_ROOT / "plugins/examples/index_worker_template",
    REPO_ROOT / "plugins/examples/md_builder_template",
)
CI_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci-dual-track.yml"


def test_case_study_docs_exist() -> None:
    for doc_path in DOC_PATHS:
        assert doc_path.exists(), f"missing case study doc: {doc_path}"


def test_case_study_docs_reference_example_directories() -> None:
    expected_refs = (
        "plugins/examples/whisper_oop_template",
        "plugins/examples/index_worker_template",
        "plugins/examples/md_builder_template",
    )
    for doc_path in DOC_PATHS:
        content = doc_path.read_text(encoding="utf-8")
        for ref in expected_refs:
            assert ref in content, f"missing reference '{ref}' in {doc_path}"


def test_case_study_example_template_files_exist() -> None:
    expected_files = (
        REPO_ROOT / "plugins/examples/README.md",
        REPO_ROOT / "plugins/examples/whisper_oop_template/manifest.json",
        REPO_ROOT / "plugins/examples/whisper_oop_template/entry.py",
        REPO_ROOT / "plugins/examples/index_worker_template/manifest.json",
        REPO_ROOT / "plugins/examples/index_worker_template/main.py",
        REPO_ROOT / "plugins/examples/md_builder_template/manifest.json",
        REPO_ROOT / "plugins/examples/md_builder_template/entry.py",
    )
    for path in expected_files:
        assert path.exists(), f"missing case study template file: {path}"


def test_case_study_template_manifests_parse() -> None:
    manifest_paths = (
        REPO_ROOT / "plugins/examples/whisper_oop_template/manifest.json",
        REPO_ROOT / "plugins/examples/index_worker_template/manifest.json",
        REPO_ROOT / "plugins/examples/md_builder_template/manifest.json",
    )

    for manifest_path in manifest_paths:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        parse_plugin_manifest(payload)


def test_ci_workflow_runs_case_study_runtime_smoke_test() -> None:
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        "gateway/tests/test_case_study_templates_runtime.py" in content
    ), "ci must run case-study runtime smoke test"
