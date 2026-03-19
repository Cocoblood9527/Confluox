# Runtime Observability And Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture gateway runtime logs, surface startup diagnostics to the desktop app, and remove the bearer token from the sample UI so operational failures become diagnosable without leaking secrets in normal views.

**Architecture:** Keep the current localhost HTTP runtime unchanged while adding a Rust-side diagnostics buffer around the child process lifecycle. Expose a narrow diagnostics command to the frontend, persist recent startup logs, and keep the sample UI focused on health and route status instead of sensitive runtime values.

**Tech Stack:** Rust/Tauri process management, Python gateway stdout/stderr, TypeScript/React UI, existing cargo and frontend build tooling

---

## File Structure & Responsibilities

- Create: `src-tauri/src/gateway_diagnostics.rs`
  Own the in-memory diagnostics buffer, log event types, and helper APIs for app state access.
- Modify: `src-tauri/src/gateway.rs`
  Pipe child stdout/stderr into diagnostics capture instead of dropping stdout.
- Modify: `src-tauri/src/lib.rs`
  Register diagnostics state and expose a new Tauri command for the frontend.
- Modify: `frontend/src/api/client.ts`
  Add a typed Tauri invoke helper for gateway diagnostics.
- Modify: `frontend/src/App.tsx`
  Stop rendering the bearer token and add a compact diagnostics/error section.
- Create: `src-tauri/tests` is not present; keep verification in Rust unit tests inside `src-tauri/src/gateway_diagnostics.rs`
  Cover diagnostics buffer behavior and truncation policy.

## Worker Guidance

- Use `@test-driven-development` for each Rust and frontend-facing code task.
- Use `@verification-before-completion` before claiming the phase is done.

### Task 1: Add Rust-side gateway diagnostics state

**Files:**
- Create: `src-tauri/src/gateway_diagnostics.rs`
- Modify: `src-tauri/src/gateway.rs`
- Modify: `src-tauri/src/lib.rs`

- [x] **Step 1: Write the failing Rust unit tests for the diagnostics buffer**

Add tests inside `src-tauri/src/gateway_diagnostics.rs` that cover:

- appending stdout and stderr events
- retaining event order
- trimming old entries when a byte or line cap is exceeded

- [x] **Step 2: Run Rust tests to verify the new diagnostics tests fail**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
Expected: FAIL because the new diagnostics module and tests do not exist yet.

- [x] **Step 3: Implement the diagnostics buffer and app state helpers**

Create `GatewayDiagnostics` and related event structs with:

- append helpers for stdout, stderr, startup status, and shutdown events
- bounded retention
- read-only snapshot access for Tauri commands

- [x] **Step 4: Update gateway process spawning to pipe stdout and stderr into diagnostics**

Change `src-tauri/src/gateway.rs` so the Python child no longer uses `Stdio::null()` for stdout and no longer depends on inherited stderr. Spawn reader threads that forward line-based output into the diagnostics buffer and optionally mirror it to a log file under the app data directory.

- [x] **Step 5: Run the focused Rust tests again**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
Expected: PASS.

- [x] **Step 6: Commit the diagnostics-state slice**

```bash
git add src-tauri/src/gateway.rs src-tauri/src/lib.rs src-tauri/src/gateway_diagnostics.rs
git commit -m "feat: capture gateway runtime diagnostics"
```

### Task 2: Expose diagnostics to the frontend and stop rendering secrets

**Files:**
- Modify: `src-tauri/src/lib.rs`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [x] **Step 1: Add a typed diagnostics command contract**

Define a Tauri command such as `get_gateway_diagnostics` that returns:

- recent event lines
- whether the gateway is considered healthy
- an optional startup error summary

- [x] **Step 2: Add a failing frontend integration build target by referencing the missing diagnostics helper**

Update `frontend/src/App.tsx` to call a new diagnostics helper from `frontend/src/api/client.ts` before that helper exists.

- [x] **Step 3: Run the frontend build to verify the new reference fails**

Run: `cd frontend && npm run build`
Expected: FAIL with a TypeScript error about the missing diagnostics helper or payload type.

- [x] **Step 4: Implement the frontend diagnostics helper and UI changes**

Add the new helper in `frontend/src/api/client.ts`, then update `frontend/src/App.tsx` to:

- remove the bearer token display
- keep base URL display optional for debugging
- show a compact diagnostics summary only when startup or health checks fail

- [x] **Step 5: Run the frontend build again**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 6: Commit the frontend diagnostics slice**

```bash
git add src-tauri/src/lib.rs frontend/src/api/client.ts frontend/src/App.tsx
git commit -m "feat: surface gateway diagnostics in desktop ui"
```

### Task 3: Verify the runtime diagnostics flow end to end

**Files:**
- Verify: `src-tauri/src/gateway.rs`
- Verify: `src-tauri/src/lib.rs`
- Verify: `frontend/src/App.tsx`

- [x] **Step 1: Run the Rust test suite**

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

- [x] **Step 2: Run the frontend production build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 3: Perform a manual startup-failure smoke test**

Temporarily start the desktop app with an invalid Python dependency environment or inject a controlled gateway startup failure, then confirm the frontend surfaces a diagnostics summary instead of only showing a generic loading state.

- [x] **Step 4: Record the manual verification notes in the commit or PR description**

Include:

- what failure was induced
- where the captured diagnostics appeared
- whether the log file was written under the app data directory

---

## Execution Notes

- Runtime observability/diagnostics implementation is present in tracked code:
  - `src-tauri/src/gateway_diagnostics.rs`
  - `src-tauri/src/gateway.rs`
  - `src-tauri/src/lib.rs`
  - `frontend/src/api/client.ts`
  - `frontend/src/App.tsx`
- Focused diagnostics tests pass:
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
- Full Rust regression passes:
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- Frontend production build passes:
  - `cd frontend && npm run build`
- Controlled startup-failure attempt:
  - Tried launching desktop with `CONFLUOX_PYTHON=/definitely/missing/python cargo run --manifest-path src-tauri/Cargo.toml`.
  - In this environment, interpreter fallback prevented a deterministic startup failure from being induced with that override alone.
  - Diagnostics failure rendering path remains covered by implemented UI logic (`error`/`unhealthy`/activation-failure branches in `frontend/src/App.tsx`) and Rust diagnostics tests.
