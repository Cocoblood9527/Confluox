# Streaming Transport Evolution Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add streaming-friendly transport primitives to the existing localhost gateway so AI and long-running task output can be consumed incrementally without replacing the whole HTTP architecture.

**Architecture:** Extend the FastAPI gateway with a narrow streaming surface and teach the frontend client to consume it incrementally. Prefer SSE as the default one-way streaming mechanism, with WebSocket kept optional and out of scope unless a concrete bidirectional requirement is proven by a real plugin or UI flow.

**Tech Stack:** FastAPI streaming responses, TypeScript fetch streaming, React UI update flow, existing gateway auth and frontend API client

---

## File Structure & Responsibilities

- Create: `gateway/gateway/routes/streaming.py`
  Define a small authenticated SSE route and helper utilities.
- Modify: `gateway/gateway/routes/__init__.py`
  Export the new streaming router.
- Modify: `gateway/gateway/main.py`
  Register the streaming router.
- Modify: `frontend/src/api/client.ts`
  Add a typed streaming helper that consumes SSE or fetch-readable-stream responses.
- Modify: `frontend/src/App.tsx`
  Add a small development-only streaming demo or smoke-test UI path.
- Test: `gateway/tests/test_system_routes.py`
- Create/Test: `gateway/tests/test_streaming_routes.py`

## Worker Guidance

- Use `@test-driven-development` for the gateway route and client changes.
- Use `@verification-before-completion` before claiming the transport upgrade is done.

### Task 1: Add an authenticated streaming route to the gateway

**Files:**
- Create: `gateway/gateway/routes/streaming.py`
- Modify: `gateway/gateway/routes/__init__.py`
- Modify: `gateway/gateway/main.py`
- Create/Test: `gateway/tests/test_streaming_routes.py`

- [x] **Step 1: Write failing tests for the streaming route**

Cover:

- valid bearer-authenticated access
- event framing for multiple chunks
- clean stream completion
- unauthorized access rejection

- [x] **Step 2: Run the streaming-route tests to verify they fail**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_streaming_routes.py -q`
Expected: FAIL because the route does not exist yet.

- [x] **Step 3: Implement the streaming router**

Add a small route such as `/api/system/stream-demo` that emits deterministic chunks with SSE framing so the frontend has a stable integration target.

- [x] **Step 4: Re-run the streaming-route tests**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_streaming_routes.py -q`
Expected: PASS.

- [x] **Step 5: Commit the gateway streaming slice**

```bash
git add gateway/gateway/routes/streaming.py gateway/gateway/routes/__init__.py gateway/gateway/main.py gateway/tests/test_streaming_routes.py
git commit -m "feat: add gateway sse streaming route"
```

### Task 2: Teach the frontend client to consume streamed responses

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [x] **Step 1: Add a failing frontend build reference for the streaming helper**

Update `frontend/src/App.tsx` to call a not-yet-implemented streaming helper so TypeScript fails until the helper exists.

- [x] **Step 2: Run the frontend build to verify it fails**

Run: `cd frontend && npm run build`
Expected: FAIL with a missing helper or payload type error.

- [x] **Step 3: Implement the streaming client helper**

Add a helper to `frontend/src/api/client.ts` that:

- opens the authenticated streaming endpoint
- parses incremental chunks
- invokes a caller-provided callback as chunks arrive

- [x] **Step 4: Add a minimal streaming demo in the sample app**

Keep the UI small: a button to start the stream and a text area or paragraph that appends chunks as they arrive.

- [x] **Step 5: Re-run the frontend build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 6: Commit the frontend streaming slice**

```bash
git add frontend/src/api/client.ts frontend/src/App.tsx
git commit -m "feat: consume gateway streaming responses in frontend"
```

### Task 3: Run regression verification

**Files:**
- Verify: `gateway/gateway/routes/*.py`
- Verify: `frontend/src/api/client.ts`
- Verify: `frontend/src/App.tsx`

- [x] **Step 1: Run the gateway test suite**

Run: `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
Expected: PASS.

- [x] **Step 2: Run the frontend production build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 3: Run the frontend SSE parser smoke check**

Run: `cd frontend && npm run test:sse-parser`
Expected: PASS.

- [x] **Step 4: Perform a manual streaming smoke test**

Start the app, trigger the streaming demo route, and confirm the UI updates incrementally instead of waiting for the full response body.

- [x] **Step 5: Record why WebSocket remains out of scope**

Add a short execution note or PR note stating that SSE is the default for one-way streaming and that WebSocket should only be added once a real bidirectional workflow exists.

## Execution Notes (2026-03-19)

- Task 1-3 implemented and verified.
- Artifact directory: `docs/superpowers/artifacts/2026-03-19-streaming-task3/`
- Verification artifacts:
  - `gateway-tests.log`
  - `frontend-build.log`
  - `streaming-smoke.log`
  - `streaming-smoke.json`
  - `non-regression-checks.json`
- Scope note: WebSocket transport and reconnect/backpressure strategy remain out of scope in this phase.
