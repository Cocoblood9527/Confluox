# Phase 2 Hardening Implementation Plan: OS Sandbox And API Isolation

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incrementally introduce worker sandbox profile policy and API execution isolation contract, while preserving compatibility and keeping scope away from streaming/websocket/reconnect.

**Architecture:** Add a policy layer on top of existing manifest/runtime model. Phase 2 starts with model + validation primitives, then wires policy gates into runtime/loader in follow-up tasks.

**Tech Stack:** Python gateway modules (`plugin_manifest`, `plugin_policy`, `plugin_runtime`, `plugin_loader`), pytest

---

## File Structure & Responsibilities

- Modify: `gateway/gateway/plugin_manifest.py`
  Add optional isolation-related manifest fields and schema checks.
- Modify: `gateway/gateway/plugin_policy.py`
  Add sandbox profile policy primitives and structured violations.
- Modify: `gateway/tests/test_plugin_manifest.py`
  Add schema tests for new manifest fields.
- Modify: `gateway/tests/test_plugin_policy.py`
  Add policy decision tests for sandbox profile gate.
- Modify: `gateway/tests/test_plugin_runtime.py` (Task 2+)
- Modify: `gateway/tests/test_plugin_loader.py` (Task 3+)
- Modify: `docs/en/plugin-guide.md` and `docs/zh-CN/plugin-guide.md` (Task 4+)

## Worker Guidance

- Use `@test-driven-development` for each task slice.
- Use `@verification-before-completion` before claiming completion.
- Keep scope tight: no streaming/websocket/reconnect changes.

### Task 1: Add worker sandbox profile policy model and tests

**Files:**
- Modify: `gateway/gateway/plugin_policy.py`
- Modify: `gateway/gateway/plugin_manifest.py`
- Modify: `gateway/tests/test_plugin_policy.py`
- Modify: `gateway/tests/test_plugin_manifest.py`

- [x] **Step 1: Write failing tests for sandbox profile policy**

Cover at minimum:

- allow worker `sandbox_profile: "restricted"` when policy allows
- reject invalid `sandbox_profile` format
- reject `sandbox_profile` outside configured allowlist
- parse worker manifest with optional `sandbox_profile`

- [x] **Step 2: Run focused tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py -q`  
Expected: FAIL before model/checks are implemented.

- [x] **Step 3: Implement minimal model + validation**

Add:

- typed worker sandbox policy structure
- decision helper returning structured violations
- manifest parse support for optional `sandbox_profile`

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py -q`  
Expected: PASS.

- [x] **Step 5: Commit Task 1 slice**

```bash
git add gateway/gateway/plugin_policy.py gateway/gateway/plugin_manifest.py gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py
git commit -m "feat: add worker sandbox profile policy model"
```

### Task 2: Enforce sandbox profile gate in worker runtime (pending)

- Runtime pre-spawn policy wiring
- Rejection reason surfaced in worker status

### Task 3: Introduce API execution mode policy contract (pending)

- Manifest execution mode schema
- Loader/runtime gate and diagnostics

### Task 4: Docs and compatibility notes (pending)

- Update bilingual plugin guides for phase 2 behavior

### Task 5: Full regression verification (pending)

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- `cd frontend && npm run build`

---

## Execution Notes

- Task 1 implemented commit trail:
  - `2102e5b feat: add worker sandbox profile policy model`
  - `c66dc61 feat: add api execution mode policy contract`
  - `bfd297c docs: update plugin policy guide for phase2 hardening`
- Follow-up phase slices were completed in dedicated plans and merged commits:
  - `2026-03-19-phase2-2-api-out-of-process-executor-plan.md`
  - `2026-03-19-worker-kernel-sandbox-hardening-plan.md`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
  - `cd frontend && npm run build`
- Boundary retained: no streaming/websocket/reconnect changes in this phase.
