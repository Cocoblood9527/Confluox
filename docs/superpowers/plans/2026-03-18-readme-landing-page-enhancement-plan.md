# README Landing Page Enhancement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the English and Chinese repository landing pages so GitHub visitors can quickly understand project fit and architecture.

**Architecture:** Update the two root README files in place, keeping the existing onboarding flow but inserting concise audience-framing sections and a clearer Markdown-friendly architecture diagram. Reuse the current detailed docs and avoid broad documentation restructuring.

**Tech Stack:** Markdown, GitHub README conventions, current repository docs structure

---

### Task 1: Enhance the English landing page

**Files:**
- Modify: `README.md`
- Reference: `docs/superpowers/specs/2026-03-18-readme-landing-page-enhancement-design.md`

- [x] **Step 1: Review the current README structure**

Run: `sed -n '1,240p' README.md`
Expected: Existing sections for overview, quick start, plugin example, integration summary, packaging, and docs links.

- [x] **Step 2: Add audience-framing sections**

Add:
- `Who is this for`
- `Who is this not for`

Expected: Both sections stay short, concrete, and aligned with the current framework scope.

- [x] **Step 3: Replace the minimal architecture block**

Add a clearer Markdown-friendly diagram and short bullets that reinforce the control flow from frontend to plugins.

- [x] **Step 4: Re-read for landing-page quality**

Run: `sed -n '1,260p' README.md`
Expected: The README remains concise and GitHub-friendly.

### Task 2: Mirror the enhancement in Chinese

**Files:**
- Modify: `README.zh-CN.md`
- Reference: `README.md`

- [x] **Step 1: Review the current Chinese README**

Run: `sed -n '1,240p' README.zh-CN.md`
Expected: The structure mirrors the English README.

- [x] **Step 2: Add the corresponding Chinese framing sections**

Add:
- `适合谁使用`
- `不适合哪些场景`

Expected: The wording reads naturally in Chinese rather than as literal translation.

- [x] **Step 3: Mirror the updated architecture presentation**

Expected: The section structure and meaning match the English README.

- [x] **Step 4: Re-read for readability**

Run: `sed -n '1,260p' README.zh-CN.md`
Expected: The README reads naturally and preserves the GitHub landing-page focus.

### Task 3: Verify alignment and repository state

**Files:**
- Verify: `README.md`
- Verify: `README.zh-CN.md`

- [x] **Step 1: Check section alignment**

Run: `rg -n "^## " README.md README.zh-CN.md`
Expected: Both files expose the same high-level section sequence.

- [x] **Step 2: Confirm implementation claims still match the codebase**

Run: `rg -n "load_api_plugins|get_gateway_info|port: 1420|frontendDist|resources" src-tauri/src gateway frontend src-tauri/tauri.conf.json frontend/vite.config.ts`
Expected: README claims about plugin loading, gateway info, dev port, and bundle resources remain grounded in source files.

- [x] **Step 3: Inspect git status**

---

## Execution Notes

- The repository landing pages now include audience framing and architecture sections in both languages:
  - `README.md`
  - `README.zh-CN.md`
- The merged commit trail for this work is represented by:
  - `9cb72fc docs: add MIT license and release metadata`
- The current tracked README structure matches the enhancement goals:
  - `Who Is This For` / `Who Is This Not For`
  - `适合谁使用` / `不适合哪些场景`
  - the expanded architecture diagram and implementation highlights

Run: `git status --short`
Expected: Only the intended documentation files appear modified or untracked.
