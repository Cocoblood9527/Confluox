# Runtime Hardening And Architecture Evolution Design

**Date:** 2026-03-18

**Goal**

Turn the architecture review findings into a staged engineering roadmap that improves observability, reduces secret exposure, tightens host-gateway lifecycle behavior, and creates a safe path toward richer plugin and streaming capabilities without destabilizing the current Confluox bridge.

## Context

The current repository already has a coherent local-bridge shape:

- Rust/Tauri starts and stops the Python gateway
- the gateway binds a random localhost port and writes a ready file
- the frontend fetches through a single authenticated local API
- plugins load as in-process FastAPI route modules

That baseline is functional, but the architecture review surfaced four clusters of risk:

1. weak observability at startup and crash time
2. unnecessary exposure of runtime secrets and control data
3. polling-based lifecycle coordination and eager plugin loading
4. lack of isolation and extensibility in the plugin runtime

The review also concluded that protocol replacement should not be the first move. The highest-return work is operational hardening around the existing localhost HTTP design.

## Scope

This design breaks the work into four implementation plans:

1. observability and runtime diagnostics
2. bootstrap, lifecycle, and startup-path hardening
3. plugin runtime evolution and isolation foundations
4. streaming-capable transport additions

These plans are intentionally sequential in priority, but not all strictly blocked on one another.

## Recommended Approach

### Phase 1: Observability first

Before changing major runtime mechanics, make failures legible.

Capture gateway stdout/stderr in Rust, persist recent logs, expose structured diagnostics to the frontend, and stop rendering the bearer token in the sample UI. This improves day-to-day debugging and lowers the risk of later refactors because regressions become easier to diagnose.

### Phase 2: Harden bootstrap and lifecycle without replacing HTTP

Keep localhost HTTP as the application protocol, but stop passing sensitive bootstrap data through process arguments and stop relying on PID polling for liveness.

The preferred incremental design is:

- Rust spawns the gateway with piped stdin
- Rust writes a single bootstrap JSON line into stdin
- Python reads that line at startup for config
- Rust keeps the pipe open for the process lifetime
- Python treats stdin EOF as host death and shuts itself down
- the existing ready-file handshake remains in place for this phase to avoid mixing too many changes

This removes the current `argv` token exposure and replaces 1-second polling with event-driven host liveness.

### Phase 3: Evolve plugin boundaries in layers

Do not attempt a big-bang replacement of the current in-process API plugin model.

Instead:

- formalize plugin manifest parsing and validation
- introduce explicit runtime metadata and permission declarations
- add a first-class `worker` or `managed_process` plugin model
- keep existing in-process API plugins working during the transition

This creates a safer path toward stronger isolation without breaking the current extension model.

### Phase 4: Add streaming-friendly transport on top of the stable core

Once diagnostics, lifecycle, and plugin boundaries are healthier, add streaming-capable interfaces where they are actually needed.

The recommended first move is SSE for one-way AI text streaming and WebSocket only if a real bidirectional requirement appears. gRPC and full UDS migration stay out of scope unless future workloads prove they are worth the added complexity.

## Alternatives Considered

### Option A: Big-bang rearchitecture now

Replace ready files, localhost HTTP, plugin loading, and lifecycle management in one sweep.

**Pros**

- removes several concerns at once
- yields the cleanest target architecture on paper

**Cons**

- too much concurrent risk for the current codebase size
- makes regressions harder to isolate
- delays delivery of the highest-value operational fixes

### Option B: Phased runtime hardening

Stabilize diagnostics and lifecycle first, then evolve plugin and transport capabilities in focused follow-up steps.

**Pros**

- highest risk-reduction per unit of change
- preserves the currently working local-HTTP architecture
- keeps each phase independently testable

**Cons**

- temporary coexistence of old and new patterns
- some review findings remain partially open between phases

**Recommendation:** choose this option.

### Option C: Protocol-first optimization

Prioritize UDS, named pipes, or gRPC before observability and lifecycle work.

**Pros**

- addresses future throughput concerns early

**Cons**

- solves a less urgent problem first
- increases integration complexity across Rust, Python, and frontend boundaries
- does little to improve crash diagnosis or plugin risk

## Workstream Boundaries

### Workstream 1: Observability And Secret Hygiene

Focus:

- gateway log capture
- startup failure diagnostics
- frontend-safe runtime display

Primary files expected to change:

- `src-tauri/src/gateway.rs`
- `src-tauri/src/lib.rs`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- new Rust-side diagnostics helper module(s)

### Workstream 2: Bootstrap And Lifecycle Hardening

Focus:

- stdin bootstrap payload
- EOF-based host liveness
- removal of PID polling
- plugin lazy loading on the startup path

Primary files expected to change:

- `src-tauri/src/gateway.rs`
- `gateway/gateway/main.py`
- `gateway/gateway/config.py`
- `gateway/gateway/host_liveness.py`
- `gateway/gateway/plugin_loader.py`
- related tests under `gateway/tests/`

### Workstream 3: Plugin Runtime Evolution

Focus:

- manifest parsing and validation
- permission declarations
- managed background plugin model
- future isolation boundary preparation

Primary files expected to change:

- `gateway/gateway/plugin_loader.py`
- new plugin manifest/runtime modules
- `gateway/gateway/process_manager.py`
- plugin docs and tests

### Workstream 4: Streaming Transport

Focus:

- SSE route support
- frontend streaming client support
- optional WebSocket path only where justified

Primary files expected to change:

- `gateway/gateway/main.py`
- new gateway streaming routes/helpers
- `frontend/src/api/client.ts`
- frontend call sites that consume streamed responses

## Verification Strategy

Each implementation plan should keep using the repository's real verification commands:

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
- `cd frontend && npm run build`

Additional phase-specific manual verification should be added where automated coverage is not yet practical, especially for startup failure surfaces and streaming behavior.

## Success Criteria

This design is successful when the follow-on plans produce a codebase where:

- gateway startup and crash failures are diagnosable from captured logs
- bearer tokens are no longer exposed in argv or the default UI
- the gateway can detect host death without 1-second PID polling
- heavy plugins no longer force all startup paths to pay their import cost
- plugin metadata has explicit room for runtime and permission policy
- streaming responses can be added without replacing the entire transport model
