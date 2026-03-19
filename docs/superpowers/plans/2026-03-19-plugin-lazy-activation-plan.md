# Plugin Lazy Activation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple plugin discovery from activation and introduce safe on-demand activation to reduce startup latency and failure blast radius.

**Architecture:** Add an activation controller and status registry over existing descriptor model. Keep current manifest compatibility, default API activation to first-request lazy mode, and preserve explicit diagnostics for activation failures.

**Tech Stack:** Python plugin loader/runtime, FastAPI route wiring, gateway diagnostics model, pytest

---

## File Structure & Responsibilities

- Create: `gateway/gateway/plugin_activation.py`
  Own activation state machine and concurrency-safe ensure-activate behavior.
- Modify: `gateway/gateway/plugin_loader.py`
  Split descriptor discovery from activation execution and expose lazy hooks.
- Modify: `gateway/gateway/main.py`
  Initialize registry/controller and wire startup strategy.
- Modify: `gateway/gateway/routes/system.py` (or dedicated diagnostics route)
  Expose activation status snapshot endpoint.
- Modify: `gateway/tests/test_plugin_loader.py`
- Create/Test: `gateway/tests/test_plugin_activation.py`
- Modify: `gateway/tests/test_main.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `docs/en/plugin-guide.md`
- Modify: `docs/zh-CN/plugin-guide.md`

## Worker Guidance

- Use `@test-driven-development` for each task.
- Use `@verification-before-completion` before marking done.
- Keep scope tight: no websocket/reconnect protocol rewrites.

### Task 1: Add activation state model and tests

**Files:**
- Create: `gateway/gateway/plugin_activation.py`
- Create/Test: `gateway/tests/test_plugin_activation.py`

- [x] **Step 1: Write failing tests for activation state transitions**

Cover:
- inactive -> activating -> active
- failure state retention with error code
- idempotent ensure-activate under repeated calls

- [x] **Step 2: Run focused tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_activation.py -q`
Expected: FAIL before implementation.

- [x] **Step 3: Implement minimal activation controller**

Add:
- typed activation state
- lock-guarded ensure-activate
- status snapshot export

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_activation.py -q`
Expected: PASS.

- [x] **Step 5: Commit activation model slice**

```bash
git add gateway/gateway/plugin_activation.py gateway/tests/test_plugin_activation.py
git commit -m "feat: add plugin activation state controller"
```

### Task 2: Integrate lazy activation into loader/main

**Files:**
- Modify: `gateway/gateway/plugin_loader.py`
- Modify: `gateway/gateway/main.py`
- Modify: `gateway/tests/test_plugin_loader.py`
- Modify: `gateway/tests/test_main.py`

- [x] **Step 1: Write failing tests for lazy API activation behavior**

Cover:
- discovery does not activate plugin side effects
- first request triggers activation
- parallel first requests still produce single activation

- [x] **Step 2: Run focused tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py gateway/tests/test_main.py -q`
Expected: FAIL before lazy wiring.

- [x] **Step 3: Implement minimal lazy wiring**

- main registers descriptors without eager activation
- request path ensures activation via controller
- startup keeps system routes healthy even when plugin activation not yet attempted

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py gateway/tests/test_main.py -q`
Expected: PASS.

- [x] **Step 5: Commit lazy wiring slice**

```bash
git add gateway/gateway/plugin_loader.py gateway/gateway/main.py gateway/tests/test_plugin_loader.py gateway/tests/test_main.py
git commit -m "feat: enable lazy activation for api plugins"
```

### Task 3: Expose activation diagnostics to UI

**Files:**
- Modify: `gateway/gateway/routes/system.py` (or dedicated diagnostics route)
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [x] **Step 1: Write failing tests for activation status endpoint**

Cover:
- endpoint returns per-plugin activation state
- failed activation exposes stable code/message

- [x] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_main.py -q`
Expected: FAIL before endpoint wiring.

- [x] **Step 3: Implement status endpoint + minimal UI section**

- add typed client fetch helper
- show compact activation status list in diagnostics area

- [x] **Step 4: Run backend and frontend checks**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_main.py -q`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 5: Commit diagnostics slice**

```bash
git add gateway/gateway/routes/system.py frontend/src/api/client.ts frontend/src/App.tsx
git commit -m "feat: expose plugin activation diagnostics"
```

### Task 4: Docs and full verification

**Files:**
- Modify: `docs/en/plugin-guide.md`
- Modify: `docs/zh-CN/plugin-guide.md`

- [x] **Step 1: Update docs for lazy activation semantics**

Document:
- default activation mode
- first-request activation behavior
- warmup guidance
- failure diagnostics visibility

- [x] **Step 2: Run full verification commands**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 3: Commit docs + verification notes**

```bash
git add docs/en/plugin-guide.md docs/zh-CN/plugin-guide.md
git commit -m "docs: describe plugin lazy activation contract"
```

---

## Execution Notes

- Implemented commit trail:
  - `02a8093 feat: add plugin activation state controller`
  - `1e5e750 feat: enable lazy activation for api plugins`
  - `f831a14 feat: expose plugin activation diagnostics`
  - `4439c33 docs: describe plugin lazy activation contract`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_activation.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py gateway/tests/test_main.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_main.py -q`
  - `cd frontend && npm run build`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- Boundary retained: no websocket/reconnect/streaming protocol rewrite in this phase.
