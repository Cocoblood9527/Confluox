# Contributing Documentation Design

**Date:** 2026-03-18

**Goal**

Add a practical, English-first contribution guide for Confluox, with a mirrored Chinese version, so early external collaborators can understand how to set up the project, what kinds of contributions are welcome, and how documentation and pull requests should be handled.

## Context

The repository now has:

- an English root README
- a Chinese root README
- mirrored English and Chinese onboarding guides
- a CI workflow that already verifies core build and test steps

What is still missing is a contributor-facing entrypoint. Without that, new contributors can read about the project, but they still have to guess:

- how to run the project locally before opening a PR
- what kinds of changes are appropriate at the current stage
- how bilingual documentation should be maintained
- what level of issue and PR detail is expected

## Scope

This design covers a standard, early-stage open-source contribution surface:

- add `CONTRIBUTING.md` as the English-first contribution guide
- add `CONTRIBUTING.zh-CN.md` as the Chinese mirror
- add links from README files to the contribution guides
- keep the guidance aligned with the repository's current maturity

This design does not include:

- a full governance model
- a code of conduct
- detailed issue templates
- detailed pull request templates
- release management policy
- formal maintainer review SLAs

## Recommended Approach

Use a "standard but lightweight" contribution guide.

That means the contribution docs should cover:

1. project setup basics
2. where to start reading
3. what kinds of contributions are especially useful right now
4. expectations for issues and pull requests
5. documentation language rules
6. a small set of guardrails about scope and repository boundaries

The tone should be welcoming, but the content should still set realistic expectations about the project's current stage.

## Alternatives Considered

### Option A: Minimal contribution guide

Only include setup and a short PR checklist.

**Pros**

- fastest to write
- lowest maintenance burden

**Cons**

- leaves too much ambiguity for new contributors
- does not reinforce bilingual documentation expectations

### Option B: Standard early-stage contribution guide

Include setup, issue and PR expectations, documentation language rules, and contribution boundaries.

**Pros**

- best fit for the current repository maturity
- gives contributors enough structure without pretending the project is more formal than it is
- supports the new English-first, bilingual documentation strategy

**Cons**

- slightly more content to maintain than a minimal guide

**Recommendation:** choose this option.

### Option C: Expanded contributor operations package

Include templates, governance notes, extensive testing policy, and release expectations.

**Pros**

- closer to a mature open-source repository surface

**Cons**

- premature for the current state of the project
- likely to introduce policy that the team is not ready to maintain yet

## Information Architecture

The English contribution guide should include:

1. Welcome
2. Before you contribute
3. Local development setup
4. Good first contribution areas
5. Issue guidelines
6. Pull request guidelines
7. Documentation and language policy
8. Scope and contribution boundaries

The Chinese guide should mirror the same structure with natural Chinese wording.

The README files should add a single contribution link in their documentation sections rather than introducing a large new top-level block.

## Content Design

### Welcome

Set a friendly tone and explain that the project is still early-stage. Encourage focused, incremental contributions over broad rewrites.

### Before you contribute

Point contributors to the README and the detailed docs first, so they build the same basic understanding before opening issues or PRs.

### Local development setup

Reuse the same setup path already described in the README and Quick Start docs:

- Python dependencies for the gateway
- Node dependencies for the frontend
- Rust and Tauri tooling
- key local commands such as `npm run dev`, `cargo tauri dev`, and gateway tests

### Good first contribution areas

Recommend contribution types that match the current maturity:

- documentation improvements
- example plugins
- gateway reliability improvements
- packaging robustness
- developer experience fixes

Avoid implying that major architectural rewrites are the ideal first contribution.

### Issue guidelines

Ask contributors to provide:

- what they expected
- what happened instead
- reproduction steps
- environment details when relevant

For feature requests, ask them to focus on use cases and constraints rather than only proposed implementation.

### Pull request guidelines

Set light but useful expectations:

- keep PRs focused
- explain what changed and why
- mention testing performed
- update docs when behavior or developer workflow changes

### Documentation and language policy

This section is especially important because the repository is now English-first but bilingual.

The guide should state:

- English is the primary GitHub-facing language
- Chinese versions should be kept in sync for user-facing docs
- contributors do not need to translate everything immediately, but docs that change public onboarding should not be left permanently unmatched

### Scope and boundaries

Make current limitations explicit:

- do not assume all plugin models are fully implemented
- do not present large architectural rewrites as default contribution paths
- avoid introducing large policy documents unless requested by maintainers

## Accuracy Constraints

The contribution guide must remain faithful to the current repository state.

It should not claim:

- that the project has a fully mature contribution process
- that maintainers guarantee rapid response times
- that full governance or release policy already exists

It should stay grounded in the current development commands and the current bilingual documentation direction.

## Testing And Verification

Verification for this work should confirm:

- both contribution guides exist and mirror the same high-level structure
- README files link to the contribution guides
- setup commands referenced in the guide match commands already documented elsewhere in the repository
- the tone stays welcoming while still setting realistic expectations

## Expected Outcome

After this work:

- the repository will have a clear early-stage contribution entrypoint
- outside contributors will have better guidance on how to participate
- bilingual documentation expectations will be discoverable and explicit
- the project will feel more ready for a public GitHub audience without pretending to be more formal than it is
