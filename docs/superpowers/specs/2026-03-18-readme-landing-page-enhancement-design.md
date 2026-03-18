# README Landing Page Enhancement Design

**Date:** 2026-03-18

**Goal**

Improve the repository landing page so first-time GitHub visitors can quickly understand what Confluox is, who it is for, and how the core layers fit together, without turning the README into a full manual.

## Context

The repository now has:

- a root English README
- a mirrored Chinese README
- detailed guides under `docs/en` and `docs/zh-CN`

That gives the project a usable documentation baseline, but the landing page still leans more toward "project notes" than "open-source front door". The next improvement should make the homepage easier to scan and easier to self-qualify against.

## Scope

This design covers a narrow README enhancement pass:

- strengthen the top-level English README
- mirror the same enhancement in the Chinese README
- add a clearer architecture diagram
- add a short "Who is this for" section
- add a short "Who is this not for" section

This design does not include:

- contribution guidelines
- release workflow docs
- issue templates
- governance or roadmap pages
- major restructuring of the detailed docs

## Recommended Approach

Use the existing README structure as the base and add two framing sections plus one improved visual block:

1. Keep the current overview, quick start, plugin example, integration summary, packaging note, and doc links.
2. Add a short "Who is this for" section near the top, after the project overview.
3. Add a short "Who is this not for" section immediately after it.
4. Replace the current minimal architecture block with a clearer README-friendly diagram and short explanatory bullets.

This approach improves project fit discovery without overloading the page.

## Alternatives Considered

### Option A: Minimal README-only polish

Only tune wording and keep the current section structure.

**Pros**

- lowest effort
- minimal risk of over-editing

**Cons**

- weak improvement in information hierarchy
- still slower for new users to decide whether the framework matches their needs

### Option B: README enhancement with audience framing and better architecture section

Add audience-fit sections plus a clearer architecture diagram while keeping README concise.

**Pros**

- highest value for GitHub first impression
- keeps homepage readable
- aligns with the project's current maturity

**Cons**

- requires careful wording so the README stays concise

**Recommendation:** choose this option.

### Option C: README plus early open-source project scaffolding

Add contribution, status, roadmap, and project governance framing now.

**Pros**

- moves closer to a complete open-source landing page

**Cons**

- likely premature for the current repository state
- risks turning the README into a policy page instead of a product entrypoint

## Information Architecture

The README should follow this flow:

1. Project title and language link
2. One-paragraph overview
3. `Who is this for`
4. `Who is this not for`
5. `Architecture at a glance`
6. `Quick start`
7. `Repository structure`
8. `Build your first plugin`
9. `Integrating an open-source project`
10. `Packaging`
11. `Documentation`
12. `Status`

The Chinese README should mirror this structure with natural Chinese phrasing rather than direct sentence-by-sentence literal translation.

## Content Design

### Who is this for

This section should help the right reader immediately recognize themselves.

It should target users such as:

- teams packaging Python capabilities behind a desktop UI
- developers exposing local tools through a controlled desktop host
- projects that already have lightweight Python service boundaries
- internal tools that benefit from unified startup, auth, and packaging behavior

### Who is this not for

This section should politely narrow expectations.

It should make clear that Confluox is not optimized for:

- zero-modification desktop wrapping of any large open-source project
- systems that require cloud orchestration rather than local hosting
- projects that expect Confluox to replace their whole application runtime immediately

### Architecture block

The new architecture block should:

- keep plain Markdown compatibility
- visually separate the four major layers
- show the direction of control and communication
- reinforce that plugins and adapters sit behind the gateway layer

The block should stay simple enough to render cleanly on GitHub without images.

## Error Handling And Accuracy Constraints

Because this is user-facing documentation, the changes must stay aligned with the actual repository state.

The README must not claim:

- that all plugin models are already fully implemented
- that any open-source project can be integrated without adaptation
- that contribution and release processes are already formalized if they are not

All examples should remain consistent with:

- the current API plugin loader
- the current dev flow using Vite on port 1420
- the current packaging flow using `dist/gateway`

## Testing And Verification

Verification for this work is documentation-focused:

- confirm both README files contain the same section structure
- confirm the new sections do not break existing document links
- confirm statements still match current implementation files
- confirm README remains concise and defers operational depth to `docs/en` and `docs/zh-CN`

## Expected Outcome

After this enhancement:

- new visitors should be able to identify project fit more quickly
- the architecture should be easier to understand from the homepage alone
- the README should feel more intentional as a GitHub landing page
- detailed docs should remain the source of deeper operational guidance
