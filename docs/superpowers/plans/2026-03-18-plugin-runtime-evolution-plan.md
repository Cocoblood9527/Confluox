# Plugin Runtime Evolution Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce explicit plugin manifest validation, runtime metadata, and a first-class managed-process worker model so Confluox can grow beyond in-process API routers without breaking current plugins.

**Architecture:** Preserve compatibility for existing `type: "api"` plugins while inserting a formal manifest layer and runtime abstraction between discovery and execution. Add a minimal `worker` plugin model that starts managed background processes through the gateway's existing process manager, and make permissions declarative so future enforcement has a stable schema to build on.

**Tech Stack:** Python manifest parsing, FastAPI plugin loading, subprocess management, Markdown plugin docs, gateway unit tests

---

## File Structure & Responsibilities

- Create: `gateway/gateway/plugin_manifest.py`
  Parse and validate plugin manifests into typed objects.
- Create: `gateway/gateway/plugin_runtime.py`
  Define runtime descriptors and worker startup helpers.
- Modify: `gateway/gateway/plugin_loader.py`
  Consume typed manifests instead of raw JSON and support `api` plus `worker`.
- Modify: `gateway/gateway/process_manager.py`
  Provide any helper methods needed for named worker registration and status tracking.
- Modify: `gateway/gateway/main.py`
  Initialize worker plugins separately from route plugins.
- Modify: `docs/zh-CN/plugin-guide.md`
  Document new manifest fields and the `worker` model.
- Modify: `docs/en/plugin-guide.md`
  Mirror the same guidance in English.
- Test: `gateway/tests/test_plugin_loader.py`
- Create/Test: `gateway/tests/test_plugin_manifest.py`
- Create/Test: `gateway/tests/test_plugin_runtime.py`

## Worker Guidance

- Use `@test-driven-development` before each manifest/runtime change.
- Use `@verification-before-completion` before marking the plan complete.

### Task 1: Add typed manifest parsing and validation

**Files:**
- Create: `gateway/gateway/plugin_manifest.py`
- Modify: `gateway/gateway/plugin_loader.py`
- Create/Test: `gateway/tests/test_plugin_manifest.py`
- Modify: `gateway/tests/test_plugin_loader.py`

- [ ] **Step 1: Write failing tests for typed manifest parsing**

Cover:

- valid legacy API manifest
- valid worker manifest with process command
- invalid `type`
- invalid `entry`
- permissions schema validation

- [ ] **Step 2: Run the manifest-focused tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_manifest.py gateway/tests/test_plugin_loader.py -q`
Expected: FAIL because typed manifest parsing does not exist yet.

- [ ] **Step 3: Implement `plugin_manifest.py` and migrate loader reads onto it**

Represent manifest fields with typed objects, keeping backward compatibility for current API plugin manifests while allowing new optional fields such as:

- `runtime`
- `permissions`
- `command`

- [ ] **Step 4: Re-run the manifest-focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_manifest.py gateway/tests/test_plugin_loader.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the manifest slice**

```bash
git add gateway/gateway/plugin_manifest.py gateway/gateway/plugin_loader.py gateway/tests/test_plugin_manifest.py gateway/tests/test_plugin_loader.py
git commit -m "feat: add typed plugin manifest parsing"
```

### Task 2: Introduce a managed worker plugin runtime

**Files:**
- Create: `gateway/gateway/plugin_runtime.py`
- Modify: `gateway/gateway/process_manager.py`
- Modify: `gateway/gateway/main.py`
- Create/Test: `gateway/tests/test_plugin_runtime.py`
- Modify: `gateway/tests/test_process_manager.py`

- [ ] **Step 1: Write failing tests for worker plugin startup**

Add tests that verify:

- a worker plugin command is launched through `ProcessManager`
- worker processes are tracked for shutdown
- invalid worker manifests are rejected before spawn

- [ ] **Step 2: Run the worker-runtime tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_runtime.py gateway/tests/test_process_manager.py -q`
Expected: FAIL because worker runtime support does not exist yet.

- [ ] **Step 3: Implement the worker runtime abstraction**

Create a minimal runtime layer that can:

- start worker plugin commands during gateway startup
- register those processes with `ProcessManager`
- return status metadata suitable for future diagnostics

- [ ] **Step 4: Update gateway startup to initialize worker plugins after manifest discovery**

Keep in-process API route plugins working exactly as before while starting worker plugins through the new runtime layer.

- [ ] **Step 5: Re-run the worker-runtime tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_runtime.py gateway/tests/test_process_manager.py -q`
Expected: PASS.

- [ ] **Step 6: Commit the worker-runtime slice**

```bash
git add gateway/gateway/plugin_runtime.py gateway/gateway/process_manager.py gateway/gateway/main.py gateway/tests/test_plugin_runtime.py gateway/tests/test_process_manager.py
git commit -m "feat: add managed worker plugin runtime"
```

### Task 3: Document the new plugin contract and permission model

**Files:**
- Modify: `docs/zh-CN/plugin-guide.md`
- Modify: `docs/en/plugin-guide.md`

- [ ] **Step 1: Update the plugin guides with new manifest fields**

Document:

- `type: "api"` versus `type: "worker"`
- `runtime`
- `permissions`
- `command`

- [ ] **Step 2: Add one worker-plugin example to each guide**

Keep the example narrow and aligned with the implemented runtime model.

- [ ] **Step 3: Re-read both docs for compatibility language**

Run: `rg -n "worker|permissions|runtime|command" docs/zh-CN/plugin-guide.md docs/en/plugin-guide.md`
Expected: the new model is documented in both languages without implying full process sandboxing already exists.

- [ ] **Step 4: Commit the documentation slice**

```bash
git add docs/zh-CN/plugin-guide.md docs/en/plugin-guide.md
git commit -m "docs: describe worker plugin runtime and manifest permissions"
```

### Task 4: Run regression verification

**Files:**
- Verify: `gateway/gateway/*.py`
- Verify: `gateway/tests/*.py`
- Verify: `docs/en/plugin-guide.md`
- Verify: `docs/zh-CN/plugin-guide.md`

- [ ] **Step 1: Run the full gateway test suite**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

- [ ] **Step 2: Perform a manual worker-plugin smoke test**

Create a temporary worker plugin under `plugins/` that runs a simple long-lived command, then start the app and confirm the worker launches and is terminated through the existing shutdown path.

- [ ] **Step 3: Capture what remains intentionally out of scope**

Record in the PR or execution notes that this phase does not yet provide full process sandboxing or API-plugin out-of-process isolation.

