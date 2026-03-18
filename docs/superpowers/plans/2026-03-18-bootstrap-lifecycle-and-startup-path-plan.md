# Bootstrap Lifecycle And Startup Path Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove secret-bearing bootstrap arguments, replace PID polling with pipe-driven host liveness, and stop forcing all plugins to load on the gateway startup path.

**Architecture:** Keep the current ready-file port handshake for this phase, but move gateway bootstrap config into a single JSON line written over child stdin. Hold that pipe open for the life of the host so Python can treat stdin EOF as host death. At the same time, refactor plugin loading into a discover/register flow so heavy plugin imports can be deferred until the plugin's routes are actually needed.

**Tech Stack:** Rust child-process IO, Python FastAPI gateway bootstrap, Python threading/IO, gateway tests, existing ready-file handshake

---

## File Structure & Responsibilities

- Modify: `src-tauri/src/gateway.rs`
  Write bootstrap JSON over child stdin and retain the write handle for lifecycle ownership.
- Modify: `src-tauri/src/lib.rs`
  Allow degraded app startup when gateway fails pre-ready so diagnostics remain queryable.
- Create: `gateway/gateway/bootstrap.py`
  Parse the one-line bootstrap payload from stdin into a validated runtime config object.
- Modify: `gateway/gateway/config.py`
  Remove fields that no longer belong on the command line and tighten remaining validation.
- Modify: `gateway/gateway/main.py`
  Use bootstrap config, start EOF-based host liveness, and avoid eager plugin imports.
- Modify: `gateway/gateway/host_liveness.py`
  Replace polling helpers with pipe-driven host shutdown helpers while preserving unit-testable interfaces.
- Modify: `gateway/gateway/plugin_loader.py`
  Split plugin discovery from route registration so lazy activation is possible.
- Test: `gateway/tests/test_config.py`
- Test: `gateway/tests/test_host_liveness.py`
- Test: `gateway/tests/test_main_ready.py`
- Test: `gateway/tests/test_plugin_loader.py`

## Worker Guidance

- Use `@test-driven-development` for gateway-side refactors.
- Use `@verification-before-completion` before marking the plan done.

## Smoke Test Evidence Standard

- Every manual smoke test must include `文字结论 + artifact`.
- Artifact must be one of:
  - screenshot evidence, or
  - machine-readable JSON/log artifact.
- If screenshots are not practical in the current environment, provide JSON/log artifacts by default.

### Task 1: Make pre-ready startup failures non-fatal and keep diagnostics visible

**Files:**
- Modify: `src-tauri/src/lib.rs`
- Modify: `src-tauri/src/gateway.rs`
- Verify: `src-tauri/src/gateway_diagnostics.rs`
- Verify: `frontend/src/App.tsx`

- [x] **Step 1: Reproduce the current fatal pre-ready startup failure (red verification)**

Run the desktop app with a controlled failing Python bootstrap environment (for example, `CONFLUOX_PYTHON` pointing to a stub that exits non-zero after dependency probe).

Run: `CONFLUOX_PYTHON=/tmp/confluox-fake-python cargo run --manifest-path src-tauri/Cargo.toml`
Expected: FAIL because app setup exits fatally before frontend can render.

- [x] **Step 2: Implement the minimal degraded startup path**

Keep diagnostics state registration as-is, but do not treat gateway pre-ready startup failure as a fatal app setup error. Preserve the localhost HTTP design and avoid broad lifecycle refactors. Ensure frontend can still load and query diagnostics even when gateway runtime is unavailable.

- [x] **Step 3: Verify core builds/tests still pass**

Run:

- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- `cd frontend && npm run build`

Expected: PASS.

- [x] **Step 4: Run startup-failure smoke test with artifact**

Induce pre-ready startup failure again and verify:

- host process no longer exits fatally during setup
- frontend starts
- diagnostics remain readable from existing diagnostics surfaces

Record `文字结论 + artifact` (screenshot or JSON/log export).

- [x] **Step 5: Commit the non-fatal startup slice**

```bash
git add src-tauri/src/lib.rs src-tauri/src/gateway.rs
git commit -m "fix: keep app alive on gateway pre-ready failure"
```

### Task 2: Move bootstrap secrets off argv and onto stdin

**Files:**
- Create: `gateway/gateway/bootstrap.py`
- Modify: `gateway/gateway/config.py`
- Modify: `gateway/gateway/main.py`
- Modify: `src-tauri/src/gateway.rs`
- Test: `gateway/tests/test_config.py`
- Test: `gateway/tests/test_main_ready.py`

- [x] **Step 1: Write failing gateway tests for stdin bootstrap parsing**

Add tests that cover:

- valid bootstrap JSON line parsing
- missing required fields
- malformed JSON
- blank stdin payload

- [x] **Step 2: Run the focused gateway tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_config.py gateway/tests/test_main_ready.py -q`
Expected: FAIL because stdin bootstrap parsing is not implemented yet.

- [x] **Step 3: Implement `bootstrap.py` and narrow `config.py` to non-secret CLI fields**

Keep only durable boot-time flags on the CLI, such as the ready-file path if still needed in this phase. Parse `data_dir`, `auth_token`, and `allowed_origin` from the bootstrap JSON line read from stdin.

- [x] **Step 4: Update Rust spawn logic to write the bootstrap JSON line**

In `src-tauri/src/gateway.rs`, create the child with piped stdin, serialize the bootstrap payload as one newline-terminated JSON object, write it once after spawn, and retain the write handle inside runtime state so the pipe stays open.

- [x] **Step 5: Re-run the focused gateway tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_config.py gateway/tests/test_main_ready.py -q`
Expected: PASS.

- [x] **Step 6: Commit the bootstrap-channel slice**

```bash
git add src-tauri/src/gateway.rs gateway/gateway/bootstrap.py gateway/gateway/config.py gateway/gateway/main.py gateway/tests/test_config.py gateway/tests/test_main_ready.py
git commit -m "feat: move gateway bootstrap onto stdin"
```

### Task 3: Replace PID polling with EOF-based host liveness

**Files:**
- Modify: `gateway/gateway/host_liveness.py`
- Modify: `gateway/gateway/main.py`
- Test: `gateway/tests/test_host_liveness.py`

- [x] **Step 1: Write failing host-liveness tests for EOF-triggered shutdown**

Add tests that simulate:

- an open pipe that keeps the watch alive
- EOF that triggers shutdown
- callback invocation exactly once

- [x] **Step 2: Run the host-liveness tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_host_liveness.py -q`
Expected: FAIL because the implementation still polls host PID.

- [x] **Step 3: Implement a pipe-driven liveness watcher**

Add a helper that blocks on the bootstrap stdin stream after the first line is consumed and triggers `on_host_exit` when EOF is observed. Remove `_watch_host_pid` and stop depending on `time.sleep(1.0)` polling in the main runtime.

- [x] **Step 4: Run the host-liveness tests again**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_host_liveness.py -q`
Expected: PASS.

- [x] **Step 5: Commit the liveness slice**

```bash
git add gateway/gateway/host_liveness.py gateway/gateway/main.py gateway/tests/test_host_liveness.py
git commit -m "feat: detect host exit via bootstrap pipe eof"
```

### Task 4: Split plugin discovery from activation and defer heavy imports

**Files:**
- Modify: `gateway/gateway/plugin_loader.py`
- Modify: `gateway/gateway/main.py`
- Test: `gateway/tests/test_plugin_loader.py`

- [x] **Step 1: Write failing plugin-loader tests for discovery without import side effects**

Add tests that verify:

- plugin manifests can be discovered without importing the entry module
- activation happens only when explicitly requested
- non-API plugins remain ignored in this phase

- [x] **Step 2: Run the plugin-loader tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py -q`
Expected: FAIL because discovery and activation are not currently separated.

- [x] **Step 3: Implement a two-stage plugin loader**

Refactor `plugin_loader.py` so it can:

- scan and validate manifests into descriptors
- activate only the descriptors requested on startup
- keep room for future lazy activation hooks

- [x] **Step 4: Update gateway startup to activate only baseline plugins**

Keep the current example plugin working, but make the startup path descriptor-driven instead of import-all-by-default.

- [x] **Step 5: Re-run the plugin-loader tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_plugin_loader.py -q`
Expected: PASS.

- [x] **Step 6: Commit the startup-path slice**

```bash
git add gateway/gateway/plugin_loader.py gateway/gateway/main.py gateway/tests/test_plugin_loader.py
git commit -m "refactor: separate plugin discovery from activation"
```

### Task 5: Run regression verification

**Files:**
- Verify: `src-tauri/src/gateway.rs`
- Verify: `gateway/gateway/*.py`
- Verify: `gateway/tests/*.py`

- [x] **Step 1: Run the full gateway test suite**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

- [x] **Step 2: Run the Rust test suite**

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

- [x] **Step 3: Perform a manual host-exit smoke test**

Start the desktop app, then kill the host process and confirm the gateway exits immediately from stdin EOF rather than lingering until a polling interval expires.

- [x] **Step 4: Record smoke-test evidence using the standard**

For each manual smoke test in this task, include `文字结论 + artifact` (screenshot or machine-readable JSON/log output).

## Execution Artifacts (This Run)

- `/tmp/task5-host-exit-smoke.json`
- `/tmp/task5-host-exit-run.log`
- `/tmp/task5-degraded-startup.json`
- `/tmp/task5-degraded-run.log`
- `/tmp/task5-stdin-bootstrap.json`
- `/tmp/task5-stdin-stderr.log`
- `/tmp/task4-plugin-loader-tests.log`
- `/tmp/task4-gateway-full-tests.log`
- `/Users/zhongliang/Library/Application Support/com.confluox.desktop/gateway.runtime.log`
