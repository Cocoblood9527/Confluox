# Pull Request Template Design

**Date:** 2026-03-18

**Goal**

Add a lightweight pull request template so contributors opening PRs on GitHub are prompted to provide the minimum context needed for efficient review, without introducing process overhead that is too heavy for the current stage of Confluox.

## Context

The repository now has:

- English-first README and mirrored Chinese README
- English and Chinese contribution guides
- a clear early-stage contribution posture

What is still missing is a GitHub-native prompt at PR creation time. Without it, contributors may still forget to explain:

- what changed
- why it changed
- how it was tested
- whether docs were updated

## Scope

This design covers:

- add `.github/PULL_REQUEST_TEMPLATE.md`

This design does not include:

- issue templates
- GitHub form-based templates
- multiple PR template variants
- release checklist templates
- heavy review policy or maintainer workflow rules

## Recommended Approach

Use a single lightweight Markdown PR template with a short structure:

1. Summary
2. Why this change
3. How to test
4. Documentation updates
5. Checklist

The template should be concise enough that contributors will actually fill it out, but specific enough to improve review quality.

## Alternatives Considered

### Option A: No PR template

**Pros**

- no maintenance

**Cons**

- contributors have no prompt at the moment of PR creation
- review quality depends too heavily on contributor habits

### Option B: Single lightweight PR template

**Pros**

- best fit for an early-stage project
- low friction
- reinforces the contribution guide without duplicating all of it

**Cons**

- still requires some periodic maintenance as process evolves

**Recommendation:** choose this option.

### Option C: Multiple detailed templates and policy-heavy structure

**Pros**

- more process coverage

**Cons**

- too heavy for the current stage
- likely to reduce completion quality by encouraging form fatigue

## Content Design

The template should prompt contributors to say:

- what changed
- why the change matters
- how reviewers can validate it
- whether any docs need to be updated

The checklist should stay intentionally small.

Suggested checklist themes:

- PR stays focused
- validation was performed
- docs were updated when needed
- bilingual public docs were considered when onboarding or usage changed

## Accuracy Constraints

The template must reflect the actual contribution expectations already documented in `CONTRIBUTING.md` and `CONTRIBUTING.zh-CN.md`.

It should not imply:

- a fully formal review process
- mandatory release notes for every PR
- governance workflows that do not yet exist

## Testing And Verification

Verification should confirm:

- `.github/PULL_REQUEST_TEMPLATE.md` exists
- the template is short and readable
- the prompts align with the contribution guide

## Expected Outcome

After this work:

- contributors will have a clear PR prompt inside GitHub
- maintainers will get more useful review context by default
- the repository's open-source surface will feel more complete without becoming process-heavy
