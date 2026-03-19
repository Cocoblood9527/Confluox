# Local Security Surface Reduction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce local attack surface by introducing scoped short-lived tokens, rotation-safe client refresh, and diagnostics redaction without breaking existing gateway flows.

**Architecture:** Keep the current localhost topology but split token responsibilities by channel. Add TTL and rotation contract to host-gateway auth, redact sensitive values in diagnostics, and provide backward-compatible migration switches.

**Tech Stack:** Rust/Tauri gateway bootstrap, Python auth middleware, frontend API client, diagnostics pipeline, pytest + cargo test

---

## File Structure & Responsibilities

- Modify: `src-tauri/src/gateway.rs`
  Issue scoped runtime tokens and expose refresh command contract.
- Modify: `src-tauri/src/lib.rs`
  Register token refresh command and state.
- Modify: `gateway/gateway/auth.py`
  Support expiring/scoped token validation.
- Modify: `gateway/gateway/bootstrap.py`
  Parse token metadata contract (ttl/scope/issued_at).
- Modify: `gateway/gateway/main.py`
  Wire token validation policy into app startup.
- Modify: `src-tauri/src/gateway_diagnostics.rs`
  Apply sensitive-value redaction before frontend exposure.
- Modify: `frontend/src/api/client.ts`
  Handle token refresh and retry-on-expired behavior.
- Modify: `frontend/src/App.tsx`
  Keep UI free of sensitive runtime data.
- Create/Test: `gateway/tests/test_auth_token_lifecycle.py`
- Modify: `gateway/tests/test_auth.py`
- Modify: `gateway/tests/test_config.py`
- Modify: `src-tauri/src/gateway_diagnostics.rs` tests
- Modify: `frontend/src/api/client.test.ts` (if test harness present)
- Modify: `docs/en/quick-start.md`
- Modify: `docs/zh-CN/quick-start.md`

## Worker Guidance

- Use `@test-driven-development` for each security slice.
- Use `@verification-before-completion` before completion claims.
- Keep scope tight: no unrelated transport refactor.

### Task 1: Add expiring/scoped token contract in gateway auth

**Files:**
- Modify: `gateway/gateway/auth.py`
- Modify: `gateway/gateway/bootstrap.py`
- Create/Test: `gateway/tests/test_auth_token_lifecycle.py`
- Modify: `gateway/tests/test_auth.py`

- [x] **Step 1: Write failing tests for ttl/scope validation**

Cover:
- valid scoped token passes
- expired token rejected with stable code
- wrong scope rejected

- [x] **Step 2: Run focused tests to verify failure**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_auth.py gateway/tests/test_auth_token_lifecycle.py -q`
Expected: FAIL before implementation.

- [x] **Step 3: Implement minimal expiring/scoped token checks**

- extend bootstrap payload parsing for token metadata
- validate expiry and scope in auth middleware
- return structured 401 payload code

- [x] **Step 4: Re-run focused tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_auth.py gateway/tests/test_auth_token_lifecycle.py -q`
Expected: PASS.

- [x] **Step 5: Commit auth lifecycle slice**

```bash
git add gateway/gateway/auth.py gateway/gateway/bootstrap.py gateway/tests/test_auth.py gateway/tests/test_auth_token_lifecycle.py
git commit -m "feat: add scoped expiring gateway auth tokens"
```

### Task 2: Add host-side refresh flow and frontend retry

**Files:**
- Modify: `src-tauri/src/gateway.rs`
- Modify: `src-tauri/src/lib.rs`
- Modify: `frontend/src/api/client.ts`

- [x] **Step 1: Write failing tests for token refresh command path**

Cover:
- refresh command issues new token metadata
- client retries once on token-expired response

- [x] **Step 2: Run targeted checks to verify failure**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway -- --nocapture`
Expected: FAIL before refresh wiring.

- [x] **Step 3: Implement minimal refresh flow**

- add Tauri command to fetch fresh scoped token
- client invalidates cached token on expired code and retries once

- [x] **Step 4: Re-run targeted checks**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway -- --nocapture`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 5: Commit refresh slice**

```bash
git add src-tauri/src/gateway.rs src-tauri/src/lib.rs frontend/src/api/client.ts
git commit -m "feat: add gateway token refresh flow"
```

### Task 3: Add diagnostics redaction baseline

**Files:**
- Modify: `src-tauri/src/gateway_diagnostics.rs`
- Modify: `gateway/gateway/main.py` (if needed for emitter-side tags)

- [x] **Step 1: Write failing tests for redaction behavior**

Cover:
- bearer-like tokens are masked
- auth headers are masked
- non-sensitive logs remain unchanged

- [x] **Step 2: Run focused Rust tests to verify failure**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
Expected: FAIL before redaction rules.

- [x] **Step 3: Implement minimal redaction pass**

- redact token-like substrings in diagnostics response path
- keep raw internal storage optional but frontend response masked by default

- [x] **Step 4: Re-run focused Rust tests**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
Expected: PASS.

- [x] **Step 5: Commit redaction slice**

```bash
git add src-tauri/src/gateway_diagnostics.rs gateway/gateway/main.py
git commit -m "feat: redact sensitive fields in diagnostics output"
```

### Task 4: Docs + full verification

**Files:**
- Modify: `docs/en/quick-start.md`
- Modify: `docs/zh-CN/quick-start.md`

- [x] **Step 1: Update docs for token lifecycle and security notes**

Document:
- token ttl behavior
- refresh contract
- diagnostics redaction guarantees

- [x] **Step 2: Run full verification chain**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 3: Commit docs slice**

```bash
git add docs/en/quick-start.md docs/zh-CN/quick-start.md
git commit -m "docs: describe scoped token lifecycle and diagnostics redaction"
```

---

## Execution Notes

- Implemented commit trail:
  - `16655b0 feat: add scoped expiring gateway auth tokens`
  - `d127192 feat: add gateway token refresh flow`
  - `2a0dfce feat: redact sensitive fields in diagnostics output`
  - `57b4c99 docs: describe scoped token lifecycle and diagnostics redaction`
- Validation evidence:
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_auth.py gateway/tests/test_auth_token_lifecycle.py -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway -- --nocapture`
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway_diagnostics -- --nocapture`
  - `cd frontend && npm run build`
  - `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- Boundary retained: no unrelated transport refactor in this phase.
