# Confluox v0.2.4: Case-Study Templates and Runtime Smoke Tests

Release date: 2026-03-19
Tag: `v0.2.4-case-study-templates-and-smoke-tests`

## Highlights

- Added copyable plugin templates under `plugins/examples/` for documented case studies.
- Added runtime smoke tests to ensure case-study templates stay executable.
- Added CI checks to enforce case-doc/template consistency and runtime coverage.

## What Landed

### 1. Example Templates

- `plugins/examples/whisper_oop_template`
- `plugins/examples/index_worker_template`
- `plugins/examples/md_builder_template`

### 2. Runtime Smoke Coverage

- Added `gateway/tests/test_case_study_templates_runtime.py`
- Covered:
  - in-process template route roundtrip (`/api/md/build`)
  - out-of-process template proxy roundtrip (`/api/whisper_app/transcribe`)

### 3. CI Guardrail

- `ci-dual-track` now runs:
  - `gateway/tests/test_case_study_assets.py`
  - `gateway/tests/test_case_study_templates_runtime.py`

## Verification Snapshot

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_assets.py -q` -> pass
- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_templates_runtime.py -q` -> pass
- `cd gateway && python3 -m pytest tests -q` -> pass
