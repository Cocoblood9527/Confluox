# Repository Hygiene And Process Alignment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove tracked frontend starter leftovers, document local environment isolation expectations, and align local Superpowers plan status with the repository's actual completion state.

**Architecture:** Keep the cleanup narrow and non-behavioral. Delete clearly unused frontend starter assets and styles, add concise setup guidance at the repository entrypoints, and update ignored local planning artifacts so they mirror the code and commit history already present in the repo.

**Tech Stack:** Markdown, CSS, TypeScript/React repository structure, git history, existing build/test commands

---

## File Structure & Responsibilities

- Delete: `frontend/README.md`
  Removes the tracked Vite starter README that no longer describes Confluox.
- Delete: `frontend/src/assets/hero.png`
  Removes an unused starter asset.
- Delete: `frontend/src/assets/react.svg`
  Removes an unused starter asset.
- Delete: `frontend/src/assets/vite.svg`
  Removes an unused starter asset.
- Modify: `frontend/src/App.css`
  Remove selectors that are no longer used by the current app markup.
- Modify: `frontend/src/index.css`
  Remove starter-oriented variables and selectors that are no longer referenced.
- Modify: `README.md`
  Add a short note about editable installs and worktree-aware local setup.
- Modify: `README.zh-CN.md`
  Mirror the same local setup note in Chinese.
- Modify: `docs/superpowers/plans/2026-03-18-docs-internationalization-plan.md`
  Update local checklist state to match the already-merged docs work.
- Modify: `docs/superpowers/plans/2026-03-18-readme-landing-page-enhancement-plan.md`
  Update local checklist state to match the already-merged README work.

### Task 1: Remove tracked frontend starter leftovers

**Files:**
- Delete: `frontend/README.md`
- Delete: `frontend/src/assets/hero.png`
- Delete: `frontend/src/assets/react.svg`
- Delete: `frontend/src/assets/vite.svg`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/index.css`

- [x] **Step 1: Confirm the leftovers are not referenced by the current app**

Run: `rg -n --hidden -S "react.svg|vite.svg|hero.png|counter|hero|next-steps|spacer|ticks" frontend -g '!frontend/node_modules/**'`
Expected: matches only appear in the starter files themselves, not in active app code paths.

- [x] **Step 2: Remove the tracked starter files and unused CSS**

Delete the starter README and asset files, then trim `App.css` and `index.css` down to selectors used by the current `App.tsx` markup.

- [x] **Step 3: Run the frontend build to verify cleanup stays green**

Run: `cd frontend && npm run build`
Expected: PASS.

### Task 2: Add worktree-aware environment guidance

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [x] **Step 1: Add a short local environment note to the English README**

Document that editable installs should be executed from the current worktree and may need reinstalling after switching worktrees.

- [x] **Step 2: Mirror the same note in the Chinese README**

Keep the wording natural in Chinese and scoped to the same setup caveat.

- [x] **Step 3: Re-read both README files for scope discipline**

Run: `rg -n "editable|worktree|可编辑安装|worktree" README.md README.zh-CN.md`
Expected: the new note is present in both files and remains concise.

### Task 3: Align local Superpowers plan status with repository reality

**Files:**
- Modify: `docs/superpowers/plans/2026-03-18-docs-internationalization-plan.md`
- Modify: `docs/superpowers/plans/2026-03-18-readme-landing-page-enhancement-plan.md`

- [x] **Step 1: Compare existing checklist items with merged repository state**

Reference:
- `git log --oneline --decorate -n 10`
- `README.md`
- `README.zh-CN.md`
- `docs/en/*.md`
- `docs/zh-CN/*.md`

- [x] **Step 2: Mark completed checklist items and add execution notes where needed**

Update the local plan files so they no longer imply the merged documentation work is still unstarted.

- [x] **Step 3: Verify the local status counts changed as intended**

Run: `python3 - <<'PY'`
`from pathlib import Path; import re`
`for path in sorted(Path('docs/superpowers/plans').glob('2026-03-18-*.md')):`
`    text = path.read_text(encoding='utf-8')`
`    print(path.name, len(re.findall(r'^- \\[x\\]', text, re.M)), len(re.findall(r'^- \\[ \\]', text, re.M)))`
`PY`
Expected: the two updated local plan files now show completed checklist items instead of all-unchecked status.

### Task 4: Run regression verification

**Files:**
- Verify: `frontend/`
- Verify: `gateway/`
- Verify: `src-tauri/`

- [x] **Step 1: Run gateway tests**

Run: `cd gateway && python3 -m pytest tests -q`
Expected: PASS.

- [x] **Step 2: Run frontend production build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [x] **Step 3: Run Rust tests**

---

## Execution Notes

- Removed tracked frontend starter leftovers:
  - `frontend/README.md`
  - `frontend/src/assets/hero.png`
  - `frontend/src/assets/react.svg`
  - `frontend/src/assets/vite.svg`
- Reduced `frontend/src/App.css` and `frontend/src/index.css` to selectors and variables still used by the current app shell.
- Added worktree-aware editable-install guidance to:
  - `README.md`
  - `README.zh-CN.md`
- Normalized quoted `gateway[dev]` install commands across public setup docs:
  - `README.md`
  - `README.zh-CN.md`
  - `CONTRIBUTING.md`
  - `CONTRIBUTING.zh-CN.md`
  - `docs/en/quick-start.md`
  - `docs/zh-CN/quick-start.md`
- Updated local ignored plan files so they match the already-merged documentation work:
  - `docs/superpowers/plans/2026-03-18-docs-internationalization-plan.md`
  - `docs/superpowers/plans/2026-03-18-readme-landing-page-enhancement-plan.md`
- Fresh verification results:
  - `cd frontend && npm run build`
  - `cd gateway && python3 -m pytest tests -q`
  - `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`

Run: `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture`
Expected: PASS.
