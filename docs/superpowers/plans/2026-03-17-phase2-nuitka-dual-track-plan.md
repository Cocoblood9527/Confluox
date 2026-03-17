# Phase 2 Nuitka Dual-Track Packaging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在不破坏既有 PyInstaller 可用性的前提下，新增 Nuitka 打包轨道（macOS），并让 Tauri 运行时通过统一元数据契约实现“Nuitka 优先、PyInstaller 兜底”。

**Architecture:** 构建侧采用统一入口 + 分轨脚本：`build_gateway.sh` 负责参数与策略，`build_gateway_pyinstaller.sh` 与 `build_gateway_nuitka.sh` 各自负责产物生成。运行时侧从“硬编码路径猜测”改为“读取 `gateway-artifact.json` 选择入口”，使打包器差异收敛在构建层。回退策略由统一选择逻辑实现并可测试验证。

**Tech Stack:** Bash, Python 3.12, PyInstaller, Nuitka, Rust (Tauri 2.x), Serde JSON, Pytest, cargo test/build.

---

## File Structure & Responsibilities

- Create: `gateway/gateway/artifact_contract.py`  
  打包产物元数据模型、写入、读取、基础校验。
- Create: `gateway/tests/test_artifact_contract.py`  
  元数据结构与字段验证单测。
- Create: `gateway/scripts/build_gateway_pyinstaller.sh`  
  PyInstaller 轨道独立脚本，输出到 `dist/gateway/pyinstaller/` 并写 `gateway-artifact.json`。
- Create: `gateway/scripts/build_gateway_nuitka.sh`  
  Nuitka 轨道独立脚本（macOS），输出到 `dist/gateway/nuitka/` 并写 `gateway-artifact.json`。
- Modify: `gateway/scripts/build_gateway.sh`  
  统一入口，支持 `--track`、`--prefer`、`all` 模式回退策略。
- Create: `gateway/tests/test_build_gateway_cli.py`  
  入口参数解析与策略测试（通过 Python subprocess 调用脚本的轻量集成测试）。
- Create: `src-tauri/src/gateway_artifact.rs`  
  Rust 侧元数据读取与轨道选择逻辑（Nuitka 优先，PyInstaller 兜底）。
- Modify: `src-tauri/src/gateway.rs`  
  复用 `gateway_artifact.rs`，替换硬编码路径候选逻辑。
- Modify: `src-tauri/src/lib.rs`  
  引入新模块声明。
- Modify: `src-tauri/tauri.conf.json`  
  资源路径从单轨改为包含 `dist/gateway` 双轨目录。
- Create: `src-tauri/src/gateway_artifact.rs` 内 `#[cfg(test)]` 单测  
  验证选择优先级与双失败错误信息。
- Modify: `docs/superpowers/specs/2026-03-17-phase2-nuitka-dual-track-design.md`  
  记录实现后差异（仅在实现结束时补充）。

---

### Task 1: Build Artifact Contract Module (Python)

**Files:**
- Create: `gateway/gateway/artifact_contract.py`
- Create: `gateway/tests/test_artifact_contract.py`
- Test: `gateway/tests/test_artifact_contract.py`

- [x] **Step 1: Write failing tests for artifact payload validation**

```python
from gateway.artifact_contract import build_artifact_payload

def test_build_artifact_payload_contains_required_fields() -> None:
    payload = build_artifact_payload(
        track="pyinstaller",
        platform="darwin-arm64",
        entry="confluox-gateway/confluox-gateway",
        resources_dir="confluox-gateway",
        version="0.1.0",
        built_at="2026-03-17T00:00:00Z",
    )
    assert payload["track"] == "pyinstaller"
    assert payload["platform"] == "darwin-arm64"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd gateway && python3 -m pytest tests/test_artifact_contract.py -q`  
Expected: FAIL with `ModuleNotFoundError` or missing function assertions.

- [x] **Step 3: Implement artifact contract helpers**

```python
def build_artifact_payload(...)-> dict[str, str]: ...
def write_artifact_file(path: Path, payload: Mapping[str, str]) -> None: ...
def load_artifact_file(path: Path) -> dict[str, str]: ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd gateway && python3 -m pytest tests/test_artifact_contract.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gateway/gateway/artifact_contract.py gateway/tests/test_artifact_contract.py
git commit -m "feat(gateway): add artifact metadata contract helpers"
```

---

### Task 2: Split PyInstaller Track Into Dedicated Script

**Files:**
- Create: `gateway/scripts/build_gateway_pyinstaller.sh`
- Modify: `gateway/scripts/build_gateway.sh`
- Create: `gateway/tests/test_build_gateway_cli.py`
- Test: `gateway/tests/test_build_gateway_cli.py`

- [x] **Step 1: Write failing test for PyInstaller artifact metadata output**

Add test case in `gateway/tests/test_build_gateway_cli.py`:

```python
def test_pyinstaller_track_writes_artifact_file() -> None:
    # run script with --track pyinstaller
    # assert dist/gateway/pyinstaller/gateway-artifact.json exists
    # assert json["track"] == "pyinstaller"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py -q`  
Expected: FAIL because script and output path contract do not exist yet.

- [x] **Step 3: Create the dedicated PyInstaller track script**

Create `gateway/scripts/build_gateway_pyinstaller.sh` with the current PyInstaller invocation and shared plugin scan inputs.

- [x] **Step 4: Update the output layout and metadata write**

Implementation requirements:
- Keep plugin scan + hidden imports behavior.
- Output path becomes `dist/gateway/pyinstaller/`.
- Write `gateway-artifact.json` via `artifact_contract.py`.
- Keep executable name compatibility (`confluox-gateway`).

- [x] **Step 5: Update the entry script to call the track script**

Modify `gateway/scripts/build_gateway.sh` so `--track pyinstaller` delegates to `build_gateway_pyinstaller.sh`.

- [x] **Step 6: Run test to verify it passes**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py::test_pyinstaller_track_writes_artifact_file -q`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add gateway/scripts/build_gateway_pyinstaller.sh gateway/scripts/build_gateway.sh gateway/tests/test_build_gateway_cli.py
git commit -m "refactor(gateway): split pyinstaller track script with artifact metadata"
```

---

### Task 3: Add Nuitka Track Script (macOS)

**Files:**
- Create: `gateway/scripts/build_gateway_nuitka.sh`
- Modify: `gateway/tests/test_build_gateway_cli.py`
- Test: `gateway/tests/test_build_gateway_cli.py`

- [x] **Step 1: Write failing test for Nuitka track artifact output**

```python
def test_nuitka_track_writes_artifact_file() -> None:
    # run script with --track nuitka
    # assert dist/gateway/nuitka/gateway-artifact.json exists
    # assert json["track"] == "nuitka"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py::test_nuitka_track_writes_artifact_file -q`  
Expected: FAIL due to missing Nuitka script/track.

- [x] **Step 3: Create the Nuitka track script**

Implementation requirements:
- macOS-only guard (`uname` check, clear error message on unsupported OS).
- Ensure dependencies present (`python3 -m nuitka --version` or actionable error).
- Produce output under `dist/gateway/nuitka/`.
- Include plugin resources.
- Write `gateway-artifact.json` with track=`nuitka`.

- [x] **Step 4: Hook the entry script to the new track**

Modify `gateway/scripts/build_gateway.sh` so `--track nuitka` delegates to `build_gateway_nuitka.sh`.

- [x] **Step 5: Run test to verify it passes**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py::test_nuitka_track_writes_artifact_file -q`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gateway/scripts/build_gateway_nuitka.sh gateway/tests/test_build_gateway_cli.py
git commit -m "feat(gateway): add nuitka packaging track for macos"
```

---

### Task 4: Implement Unified Build Entry With Track Strategy

**Files:**
- Modify: `gateway/scripts/build_gateway.sh`
- Modify: `gateway/tests/test_build_gateway_cli.py`
- Test: `gateway/tests/test_build_gateway_cli.py`

- [x] **Step 1: Write failing tests for `--track` and `--prefer` strategy**

```python
def test_track_all_succeeds_when_one_track_passes() -> None: ...
def test_track_nuitka_fails_when_nuitka_fails() -> None: ...
def test_prefer_flag_is_emitted_for_runtime_selection() -> None: ...
```

- [x] **Step 2: Run tests to verify failures**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py -q`  
Expected: FAIL on strategy assertions.

- [x] **Step 3: Implement `--track` parsing and exit-code behavior**

Requirements:
- Parse `--track nuitka|pyinstaller|all` (default `all`).
- `all` mode should run both tracks, tolerate single-track failure, and return non-zero only if both fail.

- [x] **Step 4: Implement `--prefer` as build-order only**

Requirements:
- Parse `--prefer nuitka|pyinstaller` (default `nuitka`).
- `--prefer` only controls execution order, logging, and验收优先级。
- Rust 运行时不得读取额外 preference 文件。

- [x] **Step 5: Run tests to verify pass**

Run: `cd gateway && python3 -m pytest tests/test_build_gateway_cli.py -q`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gateway/scripts/build_gateway.sh gateway/tests/test_build_gateway_cli.py
git commit -m "feat(gateway): add dual-track strategy flags for gateway build entry"
```

---

### Task 5: Add Rust Artifact Selection Module and Unit Tests

**Files:**
- Create: `src-tauri/src/gateway_artifact.rs`
- Modify: `src-tauri/src/gateway.rs`
- Modify: `src-tauri/src/lib.rs`
- Test: `src-tauri/src/gateway_artifact.rs`

- [x] **Step 1: Write failing Rust unit tests for track selection**

In `gateway_artifact.rs`:

```rust
#[test]
fn selects_nuitka_before_pyinstaller_when_both_exist() { ... }

#[test]
fn falls_back_to_pyinstaller_when_nuitka_missing() { ... }

#[test]
fn returns_diagnostic_error_when_no_artifact_available() { ... }
```

- [x] **Step 2: Run tests to verify failures**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`  
Expected: FAIL because module and implementation do not exist.

- [x] **Step 3: Implement metadata parsing and selection**

Requirements:
- Read `gateway-artifact.json` from `resources/gateway/nuitka` and `resources/gateway/pyinstaller`.
- Validate `entry` exists before selection.
- Ignore build-time `--prefer` once resources are packaged.
- Return actionable error with checked paths.

- [x] **Step 4: Replace old candidate-guess logic in `gateway.rs`**

`resolve_bundled_gateway_binary` should delegate to `gateway_artifact` module.

- [x] **Step 5: Run tests to verify pass**

Run: `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src-tauri/src/gateway_artifact.rs src-tauri/src/gateway.rs src-tauri/src/lib.rs
git commit -m "feat(tauri): resolve bundled gateway from artifact metadata with fallback"
```

---

### Task 6: Update Tauri Resource Mapping to Dual-Track Layout

**Files:**
- Modify: `src-tauri/tauri.conf.json`
- Test: `src-tauri/tauri.conf.json` (bundle verification via release build)

- [x] **Step 1: Write failing integration expectation**

Capture expected resource layout check command in plan runbook:

```bash
find src-tauri/target/release/bundle/macos/confluox.app/Contents/Resources/gateway -maxdepth 3 -type f
```

Expected includes:
- `.../gateway/nuitka/gateway-artifact.json`
- `.../gateway/pyinstaller/gateway-artifact.json`

- [x] **Step 2: Update resource mapping to include `../dist/gateway`**

Keep mapping explicit so bundle layout is stable.

- [x] **Step 3: Run release bundle build and verify**

Run: `cargo tauri build --no-sign`  
Run: resource `find` command above  
Expected: both track metadata files packaged.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/tauri.conf.json
git commit -m "build(tauri): package dual-track gateway artifacts as resources"
```

---

### Task 7: End-to-End Verification and Documentation Update

**Files:**
- Modify: `docs/superpowers/specs/2026-03-17-phase2-nuitka-dual-track-design.md`
- Modify: `docs/superpowers/plans/2026-03-17-phase2-nuitka-dual-track-plan.md` (checklist status update)
- Test: end-to-end command suite in this task

- [x] **Step 1: Run full verification suite**

```bash
cd gateway && python3 -m pytest tests -q
cd ../frontend && npm run build
cd .. && cargo build --manifest-path src-tauri/Cargo.toml
cd gateway && ./scripts/build_gateway.sh --track pyinstaller
cd gateway && ./scripts/build_gateway.sh --track nuitka
cd gateway && ./scripts/build_gateway.sh --track all
cd .. && cargo tauri build --no-bundle --no-sign
```

Expected:
- Tests pass
- All three track commands complete
- Tauri build completes

- [x] **Step 2: Run fallback checks**

Manual checks:
- Temporarily remove `dist/gateway/nuitka/gateway-artifact.json` and confirm runtime selects PyInstaller.
- Temporarily remove both metadata files and confirm startup error includes checked paths.

- [x] **Step 3: Update spec with execution evidence**

Record final command outputs, known limits, and decisions.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-03-17-phase2-nuitka-dual-track-design.md docs/superpowers/plans/2026-03-17-phase2-nuitka-dual-track-plan.md
git commit -m "docs: record phase2 nuitka dual-track verification evidence"
```

---

## Execution Update (2026-03-17)

- 已按计划完成所有实现与验证步骤；所有非 commit 步骤均已打勾。
- 本地验证通过：
  - `gateway` 全量测试通过（29 passed）
  - `gateway_artifact` Rust 单测通过（3 passed）
  - 双轨构建命令 `--track pyinstaller` / `--track nuitka` / `--track all` 均成功
  - `cargo tauri build --no-bundle --no-sign` 与 `cargo tauri build --no-sign` 均成功
- 回退契约通过 `gateway_artifact` 单测验证（Nuitka 优先、PyInstaller 回退、双失败诊断）。
- 预留 commit 步骤未执行，保持工作区变更供人工审阅后统一提交。

---

## Review Notes

- Apply DRY/YAGNI: 先保证双轨契约稳定，不在本轮引入 CI/perf 基准。
- 优先保证可回退：Nuitka 任意异常都不能破坏 PyInstaller 主链路。
- 尽量复用现有扫描结果与测试模式，避免平行实现。

## Plan Review Loop Result

当前会话已完成本地自审。  
严格 superpowers 流程下，外部 `plan-document-reviewer` 子代理审阅仍待你明确授权后补跑；在补跑前，本计划应视为“用户已确认、外部 reviewer 未执行”的状态。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-03-17-phase2-nuitka-dual-track-plan.md`. 在你接受“先按当前计划执行、后补 reviewer”或明确授权子代理审阅后，即可进入实现。
