# Documentation Internationalization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an English-first, GitHub-friendly documentation entrypoint with mirrored Chinese docs for onboarding and project integration.

**Architecture:** Create repository-level bilingual README files as the landing pages, then move step-by-step guidance into mirrored `docs/en` and `docs/zh-CN` subtrees. Keep README concise and product-oriented, and keep deeper operational details in guide pages that map cleanly to the current Tauri + Python gateway + React plugin architecture.

**Tech Stack:** Markdown, GitHub README conventions, existing repository structure and source code references

---

### Task 1: Define the documentation surface

**Files:**
- Create: `README.md`
- Create: `README.zh-CN.md`
- Create: `docs/en/quick-start.md`
- Create: `docs/en/plugin-guide.md`
- Create: `docs/en/integration-guide.md`
- Create: `docs/zh-CN/quick-start.md`
- Create: `docs/zh-CN/plugin-guide.md`
- Create: `docs/zh-CN/integration-guide.md`

- [x] **Step 1: Confirm the repository-level documentation entrypoints**

Run: `rg --files -g 'README*' -g 'docs/**' .`
Expected: No existing repository `README.md`; only `frontend/README.md` and planning docs exist.

- [x] **Step 2: Map content ownership by file**

Define:
- `README.md`: English landing page for GitHub visitors
- `README.zh-CN.md`: Chinese landing page mirroring the English README
- `docs/en/*.md`: Detailed English guides
- `docs/zh-CN/*.md`: Detailed Chinese guides

- [x] **Step 3: Keep content aligned with the current implementation**

Reference:
- `src-tauri/src/gateway.rs`
- `gateway/gateway/main.py`
- `gateway/gateway/plugin_loader.py`
- `plugins/example_api/entry.py`
- `src-tauri/tauri.conf.json`
- `frontend/vite.config.ts`

### Task 2: Create bilingual README landing pages

**Files:**
- Create: `README.md`
- Create: `README.zh-CN.md`

- [x] **Step 1: Draft the English README**

Include:
- Project overview
- Use cases
- Architecture at a glance
- Quick start summary
- Repository structure
- First plugin workflow
- Open-source integration paths
- Packaging note
- Documentation links

- [x] **Step 2: Draft the Chinese README**

Mirror the English README structure while adapting phrasing naturally for Chinese readers.

- [x] **Step 3: Add reciprocal language links**

Ensure each README links to the other language version near the top.

### Task 3: Create mirrored guide pages

**Files:**
- Create: `docs/en/quick-start.md`
- Create: `docs/en/plugin-guide.md`
- Create: `docs/en/integration-guide.md`
- Create: `docs/zh-CN/quick-start.md`
- Create: `docs/zh-CN/plugin-guide.md`
- Create: `docs/zh-CN/integration-guide.md`

- [x] **Step 1: Write Quick Start guides**

Cover prerequisites, install commands, local dev flow, and packaging entry points.

- [x] **Step 2: Write Plugin Guide pages**

Cover plugin folder layout, `manifest.json`, `entry.py`, `setup(context)`, and front-end calls.

- [x] **Step 3: Write Integration Guide pages**

Cover lightweight API projects, CLI/services, and complex third-party projects with realistic expectations.

### Task 4: Verify and polish

**Files:**
- Verify: `README.md`
- Verify: `README.zh-CN.md`
- Verify: `docs/en/quick-start.md`
- Verify: `docs/en/plugin-guide.md`
- Verify: `docs/en/integration-guide.md`
- Verify: `docs/zh-CN/quick-start.md`
- Verify: `docs/zh-CN/plugin-guide.md`
- Verify: `docs/zh-CN/integration-guide.md`

- [x] **Step 1: Validate file presence and internal links**

Run: `rg -n "\]\((README|docs)/" README.md README.zh-CN.md docs/en/*.md docs/zh-CN/*.md`
Expected: All documentation links point to existing Markdown files.

- [x] **Step 2: Spot-check claims against source files**

Run: `rg -n "get_gateway_info|load_api_plugins|type\": \"api\"|port: 1420|frontendDist|resources" src-tauri/src gateway plugins frontend src-tauri/tauri.conf.json frontend/vite.config.ts`
Expected: Referenced implementation details are present in the codebase.

- [x] **Step 3: Review rendered structure for readability**

---

## Execution Notes

- Repository-level bilingual entrypoints were added and later enhanced in tracked files:
  - `README.md`
  - `README.zh-CN.md`
- Mirrored onboarding guides were added in tracked docs:
  - `docs/en/quick-start.md`
  - `docs/en/plugin-guide.md`
  - `docs/en/integration-guide.md`
  - `docs/zh-CN/quick-start.md`
  - `docs/zh-CN/plugin-guide.md`
  - `docs/zh-CN/integration-guide.md`
- The merged commit trail for this work is represented by:
  - `decc71e docs: add bilingual onboarding and contribution guides`

Run: `sed -n '1,220p' README.md && sed -n '1,220p' README.zh-CN.md`
Expected: The top-level landing pages read cleanly and direct users to deeper docs without becoming too long.
