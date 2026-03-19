# Integration Guide

## The Right Expectation

Confluox is a bridge framework for local capabilities. It is not a promise that every open-source project can become a desktop app without adaptation.

The best integration path depends on what kind of project you are bringing in.

## Path 1: Lightweight API Project

Best fit:

- FastAPI apps
- APIRouter-based tools
- small Python services with clear HTTP boundaries

Recommended approach:

- extract or wrap the useful routes
- expose them through a plugin `setup(context)`
- keep state in the provided data directory
- call the plugin from the frontend

This is the lowest-friction path today.

## Path 2: CLI Tool Or Local Service

Best fit:

- command-line tools
- task runners
- local inference or automation processes
- tools that need to stay in their own process

Recommended approach:

- add an adapter layer around the tool
- start and manage the process through framework-controlled lifecycle hooks
- expose a small API surface from the gateway for the frontend
- avoid leaking raw subprocess details into the UI

This usually takes moderate integration work.

## Path 3: Large Third-Party System

Best fit:

- projects with their own frontend
- systems with heavy dependency trees
- applications that assume they are the main runtime
- services with complex streaming or session models

Recommended approach:

- isolate them behind an adapter or proxy boundary
- keep them out of the main gateway process when possible
- integrate gradually around capability boundaries
- avoid forcing full source-level unification too early

This is the highest-friction path and should be planned intentionally.

## A Practical Decision Rule

Ask these questions first:

- Can it already behave like a local API?
- Can it run safely as a managed subprocess?
- Does it need its own runtime assumptions?
- Can we expose only the capability we need instead of the whole project?

If the answer to the first question is yes, start with an API plugin.

## What To Avoid

- assuming zero modification for large projects
- importing a full third-party system directly into the main gateway process
- relying on the global working directory
- skipping data directory and resource path injection
- designing the UI before the integration boundary is stable

## Related Guides

- [Quick Start](quick-start.md)
- [Plugin Guide](plugin-guide.md)
- [Case Studies](case-studies.md)
- [中文接入指南](../zh-CN/integration-guide.md)
