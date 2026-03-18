# Contributing to Confluox

[中文版本](CONTRIBUTING.zh-CN.md)

Thanks for your interest in Confluox.

Confluox is still an early-stage framework, so the most helpful contributions are usually focused, practical improvements rather than large rewrites. Documentation, developer experience, plugin examples, gateway reliability work, and packaging improvements are all especially valuable right now.

## Before You Contribute

Before opening an issue or pull request, please read:

- [README.md](README.md)
- [Quick Start](docs/en/quick-start.md)
- [Plugin Guide](docs/en/plugin-guide.md)
- [Integration Guide](docs/en/integration-guide.md)

This helps keep discussions grounded in the current architecture and project scope.

## Local Development Setup

### Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer
- Rust toolchain
- Tauri CLI

### Install dependencies

```bash
python -m pip install -U pip
python -m pip install -e gateway[dev]
cd frontend && npm ci
cargo install tauri-cli --version "^2" --locked
```

### Start the project locally

In terminal 1:

```bash
cd frontend
npm run dev
```

In terminal 2:

```bash
cargo tauri dev
```

### Useful verification commands

Run gateway tests:

```bash
cd gateway
python -m pytest tests -q
```

Build gateway artifacts:

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

## Good First Contribution Areas

Good early contributions include:

- documentation improvements and clarification
- bilingual doc synchronization for user-facing docs
- plugin examples and example project integration notes
- gateway stability or error-handling improvements
- packaging and build workflow fixes
- small frontend usability improvements that match the current design direction

Please avoid starting with broad architectural rewrites unless the maintainers explicitly ask for them.

## Issue Guidelines

For bugs, please include:

- what you expected to happen
- what happened instead
- steps to reproduce
- logs or screenshots when helpful
- environment details when relevant

For feature requests, please focus on:

- the use case
- the problem being solved
- important constraints or trade-offs

This is usually more helpful than jumping straight to a full implementation proposal.

## Pull Request Guidelines

Please keep pull requests focused and easy to review.

A good pull request should:

- explain what changed
- explain why the change is needed
- describe how you tested it
- update docs when behavior, setup, or contributor workflow changes

When possible:

- prefer smaller PRs over large mixed changes
- avoid unrelated refactors in the same PR
- call out any follow-up work that is intentionally left out

## Documentation And Language Policy

Confluox uses an English-first documentation strategy for GitHub-facing entrypoints.

Current expectations:

- `README.md` is the primary repository landing page
- Chinese mirrors should be provided for user-facing onboarding docs
- if you change public-facing setup or usage docs, please update the matching Chinese or English version as well
- if you cannot fully translate a related doc in the same PR, call that out clearly instead of leaving it ambiguous

Perfection is not required for every small internal text change, but public onboarding docs should not drift for long.

## Scope And Contribution Boundaries

Please keep the current project maturity in mind:

- the API plugin path is the most complete integration model today
- not every plugin model described in planning docs is fully implemented yet
- Confluox is not currently a zero-effort desktop wrapper for any large third-party system
- avoid adding large governance or policy documents unless maintainers request them

If you are unsure whether an idea fits the current scope, opening an issue for discussion first is a great option.
