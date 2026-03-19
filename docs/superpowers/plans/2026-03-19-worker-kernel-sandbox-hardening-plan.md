# Worker Kernel Sandbox Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade worker sandboxing from policy-only + RLIMIT hardening to capability-aware OS-level enforcement with explicit diagnostics.

**Architecture:** Add a sandbox capability and executor abstraction between `plugin_runtime` and `process_manager`. Keep manifest/profile model compatible, but require capability checks before spawning workers for restrictive profiles. Enforce fail-closed behavior for unsupported strict profiles.

**Tech Stack:** Python gateway runtime, subprocess/process manager, platform capability probing, pytest

---

## File Structure & Responsibilities

- Create: `gateway/gateway/sandbox_capability.py`
  Detect host sandbox capabilities in a platform-aware way.
- Create: `gateway/gateway/sandbox_executor.py`
  Build and apply sandbox spawn plans from profile + capabilities.
- Modify: `gateway/gateway/process_manager.py`
  Route worker spawn through sandbox executor abstraction.
- Modify: `gateway/gateway/plugin_runtime.py`
  Surface structured runtime rejection for capability/enforcement failures.
- Modify: `gateway/gateway/main.py`
  Wire default sandbox capability policy and runtime hooks.
- Create/Test: `gateway/tests/test_sandbox_capability.py`
- Create/Test: `gateway/tests/test_sandbox_executor.py`
- Modify: `gateway/tests/test_process_manager.py`
- Modify: `gateway/tests/test_plugin_runtime.py`
- Modify: `docs/en/plugin-guide.md`
- Modify: `docs/zh-CN/plugin-guide.md`

## Worker Guidance

- Use `@test-driven-development` for each task slice.
- Use `@verification-before-completion` before any completion claims.
- Keep scope tight: no streaming/websocket/reconnect changes.

### Task 1: Add capability model and failing tests

**Files:**
- Create: `gateway/gateway/sandbox_capability.py`
- Create/Test: `gateway/tests/test_sandbox_capability.py`

- [x] **Step 1: Write failing tests for capability probing and normalization**

Cover:
- linux capability probe returns typed fields
- unsupported platform returns explicit false capabilities
- invalid probe payload is rejected

- [x] **Step 2: Run focused tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_capability.py -q`
Expected: FAIL before module implementation.

- [x] **Step 3: Implement minimal capability model**

Add:
- typed `SandboxCapabilities`
- platform probe helper
- deterministic normalization/validation

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_capability.py -q`
Expected: PASS.

- [x] **Step 5: Commit capability slice**

```bash
git add gateway/gateway/sandbox_capability.py gateway/tests/test_sandbox_capability.py
git commit -m "feat: add worker sandbox capability model"
```

### Task 2: Add sandbox executor abstraction

**Files:**
- Create: `gateway/gateway/sandbox_executor.py`
- Create/Test: `gateway/tests/test_sandbox_executor.py`

- [x] **Step 1: Write failing tests for profile-to-plan decisions**

Cover:
- `none` -> no sandbox plan
- `restricted` requires baseline capabilities
- `strict` requires stricter capabilities and fails closed when missing
- unsupported profile emits structured executor error

- [x] **Step 2: Run focused tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_executor.py -q`
Expected: FAIL before executor implementation.

- [x] **Step 3: Implement minimal sandbox plan builder**

Add:
- `SandboxSpawnPlan`
- `build_sandbox_spawn_plan(profile, capabilities)`
- explicit error codes for missing capabilities

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_executor.py -q`
Expected: PASS.

- [x] **Step 5: Commit executor slice**

```bash
git add gateway/gateway/sandbox_executor.py gateway/tests/test_sandbox_executor.py
git commit -m "feat: add worker sandbox executor abstraction"
```

### Task 3: Integrate process manager/runtime enforcement

**Files:**
- Modify: `gateway/gateway/process_manager.py`
- Modify: `gateway/gateway/plugin_runtime.py`
- Modify: `gateway/tests/test_process_manager.py`
- Modify: `gateway/tests/test_plugin_runtime.py`

- [x] **Step 1: Write failing integration tests for enforcement path**

Cover:
- process manager applies sandbox plan for restrictive profile
- capability-missing error is surfaced as structured worker rejection
- unknown profile remains fail-closed

- [x] **Step 2: Run targeted tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_process_manager.py gateway/tests/test_plugin_runtime.py -q`
Expected: FAIL before integration.

- [x] **Step 3: Implement minimal integration wiring**

- call sandbox executor from `spawn_worker`
- map executor errors to stable runtime violation codes
- preserve existing worker policy gate behavior

- [x] **Step 4: Re-run targeted tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_process_manager.py gateway/tests/test_plugin_runtime.py -q`
Expected: PASS.

- [x] **Step 5: Commit integration slice**

```bash
git add gateway/gateway/process_manager.py gateway/gateway/plugin_runtime.py gateway/tests/test_process_manager.py gateway/tests/test_plugin_runtime.py
git commit -m "feat: enforce capability-aware worker sandbox execution"
```

### Task 4: Wire startup defaults and docs

**Files:**
- Modify: `gateway/gateway/main.py`
- Modify: `docs/en/plugin-guide.md`
- Modify: `docs/zh-CN/plugin-guide.md`

- [x] **Step 1: Add default capability-aware startup wiring**

- pass host capabilities into worker startup path
- keep compatibility defaults for existing plugins

- [x] **Step 2: Update bilingual docs with capability semantics**

Clarify:
- which profiles require host capabilities
- rejection behavior when capabilities missing
- current platform limitations

- [x] **Step 3: Verify docs keyword coverage**

Run: `rg -n "sandbox|capability|restricted|strict|拒绝|降级" docs/en/plugin-guide.md docs/zh-CN/plugin-guide.md`
Expected: both docs include capability and rejection semantics.

- [x] **Step 4: Commit startup+docs slice**

```bash
git add gateway/gateway/main.py docs/en/plugin-guide.md docs/zh-CN/plugin-guide.md
git commit -m "docs: describe capability-aware worker sandbox enforcement"
```

### Task 5: Full verification

- [x] **Step 1: Run gateway test suite**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

- [x] **Step 2: Run Rust regression tests**

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

- [x] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 4: Record boundaries**

Explicitly note this phase still does not provide a full cross-platform kernel policy orchestrator.

---

## Execution Notes

- Implemented commit trail:
  - `82c53ff feat: add worker sandbox capability model`
  - `9209582 feat: add worker sandbox executor abstraction`
  - `cd18b3c feat: enforce capability-aware worker sandbox execution`
  - `6b1380f docs: describe capability-aware worker sandbox enforcement`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_capability.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_sandbox_executor.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_process_manager.py gateway/tests/test_plugin_runtime.py -q`
  - `rg -n "sandbox|capability|restricted|strict|拒绝|降级" docs/en/plugin-guide.md docs/zh-CN/plugin-guide.md`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
  - `cd frontend && npm run build`
- Boundary retained: not a full cross-platform kernel policy orchestrator.
