# Phase 2.2 Implementation Plan: API Out-Of-Process Executor

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** Implement a minimal but production-usable out-of-process API plugin execution path and preserve backward compatibility for in-process plugins.

---

## Task 1: Solidify contract (manifest/config/policy)

**Files**
- `gateway/gateway/plugin_manifest.py`
- `gateway/gateway/plugin_policy.py`
- `gateway/gateway/config.py`
- `gateway/tests/test_plugin_manifest.py`
- `gateway/tests/test_config.py`

### Steps
- [x] Red: add tests requiring `command` for `api + out_of_process`
- [x] Red: add config tests for out-of-process boot timeout settings
- [x] Green: minimal implementation for manifest/config contract
- [x] Verify targeted tests pass

## Task 2: Implement out-of-process activation runtime

**Files**
- `gateway/gateway/process_manager.py`
- `gateway/gateway/plugin_loader.py`
- `gateway/gateway/main.py`
- `gateway/tests/test_plugin_loader.py`

### Steps
- [x] Red: add tests for successful out-of-process route serving
- [x] Red: add tests for boot-time failure diagnostics (timeout/crash)
- [x] Green: implement spawn + health poll + route proxy
- [x] Verify loader-focused tests pass

## Task 3: Tighten diagnostics and non-regression

**Files**
- `gateway/gateway/plugin_loader.py`
- `gateway/tests/test_plugin_loader.py`

### Steps
- [x] Ensure explicit error codes/messages for discovery/activation/proxy failure
- [x] Ensure in-process path remains unchanged
- [x] Re-run plugin and config focused tests

## Task 4: Documentation updates

**Files**
- `docs/en/plugin-guide.md`
- `docs/zh-CN/plugin-guide.md`

### Steps
- [x] Add `out_of_process` command contract, env vars, health endpoint requirements
- [x] Clarify current support boundary
- [x] Verify keyword coverage with `rg`

## Task 5: Final verification and artifacts

### Steps
- [x] `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
- [x] `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- [x] `cd frontend && npm run build`
- [x] Manual smoke for out-of-process success/failure and artifact capture

---

## Execution Notes

- Implemented commit trail:
  - `c66dc61 feat: add api execution mode policy contract`
  - `1c6cc07 feat: implement api out-of-process executor path`
  - `5bf21ab feat: harden out-of-process api runtime channel`
  - `6f3df44 docs: add api oop security and circuit controls`
  - `86afae9 docs: describe api out-of-process runtime contract`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
  - `cd frontend && npm run build`
- Manual smoke was covered in merged execution history for out-of-process success/failure diagnostics paths.
