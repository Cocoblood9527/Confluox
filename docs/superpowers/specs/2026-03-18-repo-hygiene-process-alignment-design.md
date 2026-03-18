# Repository Hygiene And Process Alignment Design

**Date:** 2026-03-18

**Goal**

Tighten the repository surface so the tracked code better reflects the actual Confluox product, reduce avoidable local-environment confusion, and align local Superpowers planning artifacts with the implementation state that already exists in git history.

## Context

The repository is already in a strong executable state:

- gateway tests pass
- frontend production build passes
- Rust tests pass
- dual-track gateway packaging passes
- Tauri no-bundle release build passes

The remaining gaps are not core runtime failures. They are repository hygiene and process hygiene issues:

- the frontend subtree still contains obvious Vite template leftovers
- local Python editable-install state can point at a different worktree, which is confusing during verification
- local `docs/superpowers` plan files do not consistently match the code and commit history

## Scope

This cleanup covers three areas:

1. remove tracked frontend template leftovers that are no longer part of the actual app
2. document how to avoid editable-install cross-worktree confusion during local setup
3. update local Superpowers planning artifacts so their checklist state matches repository reality

This cleanup does not include:

- changing the app architecture
- adding new product features
- changing public repository policy by re-tracking `docs/superpowers`
- introducing a new lint/test framework just for hygiene checks

## Recommended Approach

Use a conservative cleanup pass that preserves current runtime behavior.

### 1. Frontend cleanup

Remove files and style blocks that clearly come from the Vite starter and are not referenced by the current Confluox UI:

- `frontend/README.md`
- unused starter assets under `frontend/src/assets/`
- unused CSS selectors and variables that no longer correspond to the rendered app

Keep the current app behavior and visual structure intact.

### 2. Environment guidance

Add a short repository-level note explaining that editable installs should be performed from the current worktree, and that developers may need to reinstall `gateway[dev]` when switching worktrees.

The note should be practical and brief, not a long environment manual.

### 3. Local process alignment

Update the local `docs/superpowers/plans/*.md` files involved in the already-completed documentation and README work so their checkbox status reflects what the repository actually contains today.

Because these files are intentionally ignored, they remain local process artifacts rather than public repository content.

## Alternatives Considered

### Option A: Leave everything as-is

**Pros**

- zero risk
- no additional work

**Cons**

- repository still looks partially scaffold-derived
- environment confusion remains easy to trigger
- process status continues to be ambiguous

### Option B: Conservative cleanup with local-process alignment

**Pros**

- improves repository trustworthiness without changing public project scope
- reduces future confusion during verification
- preserves the decision to keep Superpowers artifacts local-only

**Cons**

- requires touching both tracked and ignored files

**Recommendation:** choose this option.

### Option C: Re-track all Superpowers documents

**Pros**

- strongest public audit trail

**Cons**

- changes repository publication strategy
- increases public-facing process noise
- goes beyond the current cleanup goal

## Verification

Verification should reuse the repository's real execution commands:

- `cd gateway && python3 -m pytest tests -q`
- `cd frontend && npm run build`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`

The cleanup is successful if those commands still pass and the tracked repository no longer contains the obvious frontend template leftovers.
