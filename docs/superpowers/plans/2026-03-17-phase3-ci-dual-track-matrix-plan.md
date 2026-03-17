# Phase 3 CI Dual-Track Matrix Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立 GitHub Actions 三平台 CI 矩阵，在 PR 与 main push 上自动验证 Phase 2 双轨能力，并以严格阻断策略保护主线。

**Architecture:** 使用单 workflow + 单矩阵（macOS/Ubuntu/Windows）。workflow 含 actionlint + 三平台 job。macOS 执行完整链路（gateway tests + frontend build + 双轨构建 + Rust 轨道选择测试 + tauri no-bundle 构建），Ubuntu/Windows 执行基础校验（gateway tests + frontend build + Rust 轨道选择测试），并显式补齐 `dist/gateway` 前置目录避免 tauri build-script 报错。

**Tech Stack:** GitHub Actions YAML, Bash, Python 3, Node.js/npm, Rust/Cargo, Tauri CLI.

---

## File Structure & Responsibilities

- Create: `.github/workflows/ci-dual-track.yml`  
  三平台矩阵 workflow（触发、缓存、平台分支步骤、严格失败语义、lint job）。
- Modify: `docs/superpowers/specs/2026-03-17-phase3-ci-dual-track-matrix-design.md`  
  回填实现结果与执行证据。
- Modify: `docs/superpowers/plans/2026-03-17-phase3-ci-dual-track-matrix-plan.md`  
  更新 checklist 与执行记录。

---

### Task 1: Add CI Workflow Skeleton With Matrix and Caches

**Files:**
- Create: `.github/workflows/ci-dual-track.yml`

- [x] **Step 1: Write failing expectation for missing workflow file**

Run: `test -f .github/workflows/ci-dual-track.yml`
Expected: non-zero exit（文件尚不存在）。

- [x] **Step 2: Add workflow trigger, matrix, and toolchain setup**

Implementation requirements:
- Trigger: `pull_request` + `push` to `main`
- Matrix: `macos-latest`, `ubuntu-latest`, `windows-latest`
- Add `strategy.fail-fast: false`
- Add `defaults.run.shell: bash`
- Add dedicated `actionlint` job using `reviewdog/action-actionlint@v1`
- Include setup steps:
  - `actions/checkout@v4`
  - `actions/setup-python@v5` with pip cache
  - `actions/setup-node@v4` with npm cache
  - `dtolnay/rust-toolchain@stable`
  - `Swatinem/rust-cache@v2`

- [x] **Step 3: Verify workflow file exists and contains required keys**

Run:
`python3 - <<'PY'`
`from pathlib import Path`
`p = Path('.github/workflows/ci-dual-track.yml')`
`assert p.exists()`
`text = p.read_text(encoding='utf-8')`
`for token in ['pull_request', 'push:', 'matrix:', 'macos-latest', 'ubuntu-latest', 'windows-latest', 'fail-fast: false', 'defaults:', 'shell: bash', 'reviewdog/action-actionlint@v1']:`
`    assert token in text, token`
`print('workflow skeleton tokens verified')`
`PY`
Expected: script prints `workflow skeleton tokens verified`.

- [x] **Step 4: Commit**

```bash
git add .github/workflows/ci-dual-track.yml
git commit -m "ci: add dual-track matrix workflow skeleton"
```

---

### Task 2: Implement Platform-Specific CI Steps

**Files:**
- Modify: `.github/workflows/ci-dual-track.yml`

- [x] **Step 1: Write failing expectation for missing macOS full-chain command list**

Run:
`python3 - <<'PY'`
`from pathlib import Path`
`text = Path('.github/workflows/ci-dual-track.yml').read_text(encoding='utf-8')`
`assert 'cargo tauri build --no-bundle --no-sign' in text`
`PY`
Expected: FAIL before full command list is added.

- [x] **Step 2: Add shared steps for all OS jobs**

Implementation requirements:
- `python -m pip install -U pip`
- `python -m pip install -e gateway[dev]`
- `python -m pip install pyinstaller nuitka`
- `cd frontend && npm ci && npm run build`
- `cd gateway && python -m pytest tests -q`

- [x] **Step 3: Add macOS-only full-chain steps with strict order**

Implementation requirements:
- `if: matrix.os == 'macos-latest'`
- Ordered commands:
  1. `cd gateway && ./scripts/build_gateway.sh --track all`
  2. `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`
  3. `cargo tauri build --no-bundle --no-sign`

- [x] **Step 4: Add Ubuntu/Windows Rust-test precondition and tests**

Implementation requirements:
- `if: matrix.os != 'macos-latest'`
- Add:
  - `mkdir -p dist/gateway`
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`

- [x] **Step 5: Verify workflow structure (lint + order + conditional scoping)**

Run:
`python3 - <<'PY'`
`from pathlib import Path`
`text = Path('.github/workflows/ci-dual-track.yml').read_text(encoding='utf-8')`
`required = [`
`  'reviewdog/action-actionlint@v1',`
`  'fail-fast: false',`
`  "if: matrix.os == 'macos-latest'",`
`  "if: matrix.os != 'macos-latest'",`
`  'mkdir -p dist/gateway',`
`]`
`for token in required:`
`    assert token in text, token`
`idx_track = text.index('cd gateway && ./scripts/build_gateway.sh --track all')`
`idx_rust = text.index('cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture', idx_track)`
`idx_tauri = text.index('cargo tauri build --no-bundle --no-sign', idx_rust)`
`assert idx_track < idx_rust < idx_tauri`
`print('workflow structure and order verified')`
`PY`
Expected: script prints `workflow structure and order verified`.

- [x] **Step 6: Commit**

```bash
git add .github/workflows/ci-dual-track.yml
git commit -m "ci: add platform-specific dual-track validation steps"
```

---

### Task 3: Run Local Verification and Update Documentation Evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-03-17-phase3-ci-dual-track-matrix-design.md`
- Modify: `docs/superpowers/plans/2026-03-17-phase3-ci-dual-track-matrix-plan.md`

- [x] **Step 1: Run local command suite matching workflow intent**

Run:
```bash
set -euo pipefail
python -m pip install -U pip
python -m pip install -e gateway[dev]
python -m pip install pyinstaller nuitka
cd frontend && npm ci && npm run build
cd ../gateway && python -m pytest tests -q
cd .. && mkdir -p dist/gateway
cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture
cd gateway && ./scripts/build_gateway.sh --track all
cd .. && cargo tauri build --no-bundle --no-sign  # macOS runner expectation
```
Expected: all commands pass.

- [x] **Step 2: Update spec with execution evidence and known limits**

Add to spec:
- workflow trigger/matrix summary
- command evidence
- strict gating statement
- known limits (e.g. macOS full-chain only)
- branch protection绑定该workflow检查名的手工核验结果

- [x] **Step 3: Update this plan checklist status and execution notes**

Mark completed steps and add brief execution summary.

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-03-17-phase3-ci-dual-track-matrix-design.md docs/superpowers/plans/2026-03-17-phase3-ci-dual-track-matrix-plan.md .github/workflows/ci-dual-track.yml
git commit -m "docs: record phase3 ci dual-track matrix execution evidence"
```

---

## Execution Notes (2026-03-17)

- Task 1 red check: `test -f .github/workflows/ci-dual-track.yml` 返回 `exit:1`（符合预期）。
- Task 1 token 校验：输出 `workflow skeleton tokens verified`。
- Task 2 red check：在补齐全链路前断言 `cargo tauri build --no-bundle --no-sign` 失败（符合预期）。
- Task 2 结构校验：输出 `workflow structure and order verified`。
- Task 3 本地全链路校验通过（前端构建、gateway pytest、Rust gateway_artifact tests、dual-track build、tauri no-bundle build）。
- 本地命令兼容性修正：
  - 使用 `python3 -m ...`（当前 shell 环境无 `python` 别名）；
  - 使用 `python3 -m pip install -e "gateway[dev]"`（zsh 下避免 glob 展开）。
- Branch protection 远端核验：
  - `gh api repos/Cocoblood9527/Confluox/branches/main/protection`
  - 返回 `Branch not protected (HTTP 404)`，说明还需在 GitHub Settings 手工启用并绑定 workflow 检查项。
- 已完成提交：
  - `4133833` `ci: add dual-track matrix workflow skeleton`
  - `11f3821` `ci: add platform-specific dual-track validation steps`
  - `1c124f1` `docs: record phase3 ci dual-track matrix execution evidence`

## Review Notes

- 优先保证主线保护（strict blocking），避免“绿主线漂移”；
- 保持 YAGNI：首版不引入高级缓存与多文件 workflow 复用；
- 后续 Phase 3.1 可演进为 reusable workflows 或按 OS 拆分。

## Execution Handoff

Plan executed in `feature/phase3-ci-dual-track-matrix` with checklist completed and evidence recorded.
