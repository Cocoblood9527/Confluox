# Worker Permission Enforcement And API Trust Policy Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn worker plugin `permissions` from declarative metadata into enforced startup policy, and introduce a default-deny trust gate for non-trusted `api` plugins so third-party route plugins are blocked unless explicitly trusted.

**Architecture:** Keep the existing plugin manifest and runtime model, but add a policy layer between manifest parsing and process/router activation. For `worker` plugins, enforce an allowlist-based permission policy before process spawn. For `api` plugins, classify plugin descriptors by trust source and require explicit opt-in for untrusted descriptors. Preserve compatibility for first-party plugins under the repository `plugins/` root.

**Tech Stack:** Python plugin manifest/runtime modules, FastAPI plugin loading, subprocess process manager, gateway tests, plugin docs

---

## File Structure & Responsibilities

- Create: `gateway/gateway/plugin_policy.py`
  Central policy helpers for worker permission enforcement and API trust gating.
- Modify: `gateway/gateway/plugin_manifest.py`
  Add typed fields needed by policy checks (without breaking existing manifests).
- Modify: `gateway/gateway/plugin_loader.py`
  Attach trust metadata to API descriptors and enforce trust policy during discovery/activation.
- Modify: `gateway/gateway/plugin_runtime.py`
  Enforce worker permission policy before spawning worker processes.
- Modify: `gateway/gateway/main.py`
  Wire default policy configuration and pass policy into plugin loader/runtime calls.
- Modify: `gateway/gateway/config.py` and/or `gateway/gateway/bootstrap.py` (if needed)
  Add minimal configuration surface for trusted API sources and worker permission allowlist.
- Create/Test: `gateway/tests/test_plugin_policy.py`
- Modify: `gateway/tests/test_plugin_manifest.py`
- Modify: `gateway/tests/test_plugin_loader.py`
- Modify: `gateway/tests/test_plugin_runtime.py`
- Modify: `docs/zh-CN/plugin-guide.md`
- Modify: `docs/en/plugin-guide.md`

## Worker Guidance

- Use `@test-driven-development` for each policy slice.
- Use `@verification-before-completion` before claiming completion.
- Keep scope tight: no process sandbox implementation, no API-plugin out-of-process migration in this phase.

### Task 1: Add worker permission policy model and tests

**Files:**
- Create: `gateway/gateway/plugin_policy.py`
- Create/Test: `gateway/tests/test_plugin_policy.py`
- Modify: `gateway/tests/test_plugin_manifest.py`

- [x] **Step 1: Write failing tests for permission policy decisions**

Cover at minimum:

- allow a worker declaring `network: ["loopback"]`
- reject unknown permission namespaces
- reject invalid permission entries format
- reject permissions outside configured allowlist

- [x] **Step 2: Run focused tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py -q`
Expected: FAIL because policy module and checks do not exist yet.

- [x] **Step 3: Implement policy primitives in `plugin_policy.py`**

Add typed helpers for:

- parsing/normalizing permission declarations
- evaluating declarations against host allowlist policy
- returning structured violation reasons

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py -q`
Expected: PASS.

- [x] **Step 5: Commit policy primitives**

```bash
git add gateway/gateway/plugin_policy.py gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py
git commit -m "feat: add worker permission policy primitives"
```

### Task 2: Enforce worker permission policy before spawn

**Files:**
- Modify: `gateway/gateway/plugin_runtime.py`
- Modify: `gateway/gateway/main.py`
- Modify: `gateway/tests/test_plugin_runtime.py`

- [x] **Step 1: Write failing runtime tests for permission enforcement**

Cover:

- worker spawn allowed when permissions match policy
- worker rejected (not spawned) when permissions violate policy
- rejection reason surfaced in worker runtime status/diagnostics

- [x] **Step 2: Run runtime-focused tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_runtime.py -q`
Expected: FAIL before enforcement wiring exists.

- [x] **Step 3: Implement pre-spawn permission gate in `plugin_runtime.py`**

Ensure `start_worker_plugins(...)` evaluates each worker descriptor against policy and skips spawn when policy fails.

- [x] **Step 4: Wire policy config in `main.py`**

Provide a minimal default allowlist (safe baseline), and pass it into worker startup path.

- [x] **Step 5: Re-run runtime-focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_runtime.py -q`
Expected: PASS.

- [x] **Step 6: Commit worker enforcement slice**

```bash
git add gateway/gateway/plugin_runtime.py gateway/gateway/main.py gateway/tests/test_plugin_runtime.py
git commit -m "feat: enforce worker permissions before process spawn"
```

### Task 3: Add default-deny trust policy for untrusted API plugins

**Files:**
- Modify: `gateway/gateway/plugin_loader.py`
- Modify: `gateway/gateway/main.py`
- Modify: `gateway/tests/test_plugin_loader.py`

- [x] **Step 1: Write failing loader tests for trust gating**

Cover:

- trusted API plugin descriptors load normally
- untrusted API plugin descriptors are rejected by default
- explicit trust allowlist enables selected untrusted descriptors

- [x] **Step 2: Run loader-focused tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py -q`
Expected: FAIL before trust metadata/policy is enforced.

- [x] **Step 3: Implement trust metadata + default-deny gate**

Add descriptor trust classification and enforce:

- default behavior blocks untrusted API plugins
- explicit trusted roots/allowlist can enable them

- [x] **Step 4: Wire trust policy from startup configuration**

Keep first-party repository plugins trusted by default, and require explicit opt-in for additional API plugin sources.

- [x] **Step 5: Re-run loader-focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py -q`
Expected: PASS.

- [x] **Step 6: Commit API trust policy slice**

```bash
git add gateway/gateway/plugin_loader.py gateway/gateway/main.py gateway/tests/test_plugin_loader.py
git commit -m "feat: gate untrusted api plugins by default"
```

### Task 4: Update plugin docs for enforced policy behavior

**Files:**
- Modify: `docs/zh-CN/plugin-guide.md`
- Modify: `docs/en/plugin-guide.md`

- [x] **Step 1: Document worker permission enforcement semantics**

Clarify that:

- `permissions` is no longer metadata-only for worker startup
- policy violations prevent worker process launch

- [x] **Step 2: Document API trust defaults and opt-in path**

Clarify that untrusted API plugins are blocked by default and must be explicitly trusted.

- [x] **Step 3: Verify bilingual docs include required terms**

Run: `rg -n "permissions|enforce|trusted|untrusted|worker|api|默认|信任|拒绝" docs/zh-CN/plugin-guide.md docs/en/plugin-guide.md`
Expected: policy behavior appears in both language guides.

- [x] **Step 4: Commit docs slice**

```bash
git add docs/zh-CN/plugin-guide.md docs/en/plugin-guide.md
git commit -m "docs: describe worker permission enforcement and api trust policy"
```

### Task 5: Final regression and non-regression verification

**Files:**
- Verify: `gateway/gateway/*.py`
- Verify: `gateway/tests/*.py`
- Verify: `docs/zh-CN/plugin-guide.md`
- Verify: `docs/en/plugin-guide.md`

- [x] **Step 1: Run full gateway tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

- [x] **Step 2: Run Rust tests to confirm no host-runtime regressions**

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

- [x] **Step 3: Run frontend build to ensure no contract regressions**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 4: Perform manual policy smoke tests with artifacts**

Capture at least:

- worker allowed case (spawn succeeds)
- worker denied case (spawn rejected with reason)
- untrusted API plugin blocked by default

Record artifact paths (JSON/log) in execution notes.

- [x] **Step 5: Record out-of-scope boundaries**

Explicitly note this phase still does not provide:

- OS-level worker sandbox isolation
- full syscall/network/file enforcement beyond configured startup gate
- API plugin out-of-process execution

---

## Execution Notes

- Implemented commit trail:
  - `199a10a feat: add worker permission policy primitives`
  - `66dc60b feat: enforce worker permissions before process spawn`
  - `22a1dfe feat: gate untrusted api plugins by default`
  - `3f30edb docs: describe worker permission enforcement and api trust policy`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_policy.py gateway/tests/test_plugin_manifest.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_runtime.py -q`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py -q`
  - `rg -n "permissions|enforce|trusted|untrusted|worker|api|默认|信任|拒绝" docs/zh-CN/plugin-guide.md docs/en/plugin-guide.md`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
  - `cd frontend && npm run build`
- Boundary retained:
  - no OS-level worker sandbox isolation
  - no full syscall/network/file enforcement beyond startup gate
  - no API plugin out-of-process execution in this phase
