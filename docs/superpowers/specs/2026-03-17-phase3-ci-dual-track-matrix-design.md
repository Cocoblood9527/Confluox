# Phase 3 CI Dual-Track Matrix Design

> 状态：已实现（本地验证完成，待远端 CI 首次运行）
> 日期：2026-03-17
> 上位文档：`docs/superpowers/specs/2026-03-17-phase2-nuitka-dual-track-design.md`

## 1. 目标

建立 GitHub Actions CI 矩阵，在 `pull_request` 与 `push(main)` 上自动验证 Phase 2 双轨能力，形成严格阻断门禁。

本轮重点是：
- 覆盖 `macOS + Ubuntu + Windows` 三平台；
- `macOS` 执行完整链路（双轨构建 + Rust 选择逻辑 + Tauri no-bundle 构建）；
- `Ubuntu/Windows` 执行基础校验（gateway tests + frontend build + Rust gateway_artifact tests）；
- 三端任一失败均阻断合并。

## 2. 范围

### 2.1 In Scope

- 新增 `.github/workflows/ci-dual-track.yml`；
- 单 workflow + 单矩阵三平台；
- 基础缓存：pip / npm / cargo；
- 严格阻断策略（所有矩阵 job 必须通过）；
- 将执行证据写入 docs（spec/plan）。

### 2.2 Out of Scope

- 额外高级缓存（如 Nuitka ccache 远端缓存优化）；
- 自定义 runner 或自建缓存后端；
- Windows/Linux Nuitka 轨道实现；
- 性能/体积基准优化。

## 3. 关键决策

## 3.1 触发策略

- `pull_request`
- `push` 到 `main`

## 3.2 阻断策略

- 默认分支保护使用该 workflow 的成功状态；
- 三平台矩阵任一 job 失败，PR 不可合并。

## 3.3 平台执行内容

- macOS:
  - `cd gateway && python3 -m pytest tests -q`
  - `cd frontend && npm ci && npm run build`
  - `cd gateway && ./scripts/build_gateway.sh --track all`
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`
  - `cargo tauri build --no-bundle --no-sign`

- Ubuntu / Windows:
  - `cd gateway && python3 -m pytest tests -q`
  - `cd frontend && npm ci && npm run build`
  - `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`

## 3.4 缓存策略

- Python: `actions/setup-python` pip cache；
- Node: `actions/setup-node` npm cache；
- Rust: `Swatinem/rust-cache`；
- 暂不加入 Nuitka/ccache 额外缓存。

## 4. 可观测性与排障

- 保留关键命令原始日志输出；
- 失败直接定位到平台 + 步骤 + 命令；
- `macOS` job 重点保留双轨构建日志用于 Nuitka/PyInstaller 排障。

## 5. 验收标准

- PR 与 push(main) 均可触发该 workflow；
- 三平台 job 按策略运行对应命令；
- `macOS` 完整链路通过；
- `Ubuntu/Windows` 基础校验通过；
- workflow 状态可用于分支保护阻断。

## 6. 风险与缓解

- 首次 runner 冷启动较慢：通过 pip/npm/cargo 缓存缓解；
- Windows shell 差异：统一用 `bash` 执行脚本型步骤；
- tauri build 依赖前端产物：在 `macOS` job 中强制 `frontend build` 先于 `cargo tauri build`。

## 7. 实现结果与执行证据

### 7.1 Workflow 落地结果

- 已新增：`.github/workflows/ci-dual-track.yml`；
- 触发器：`pull_request` + `push`(`main`)；
- 门禁语义：`actionlint` job + `dual-track-matrix` job，任一失败即 workflow 失败；
- 矩阵：`macos-latest` / `ubuntu-latest` / `windows-latest`；
- 严格策略：`strategy.fail-fast: false` + `defaults.run.shell: bash`；
- 缓存：pip（`actions/setup-python`）、npm（`actions/setup-node`）、cargo（`Swatinem/rust-cache`）。

### 7.2 本地执行证据（2026-03-17）

- 骨架校验脚本输出：`workflow skeleton tokens verified`；
- 结构/顺序校验脚本输出：`workflow structure and order verified`；
- 本地全链路命令套件通过：
  - `frontend`: `npm ci && npm run build` 成功；
  - `gateway`: `python3 -m pytest tests -q`，`29 passed`；
  - Rust 轨道测试：`cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`，`4 passed`；
  - 双轨构建：`./scripts/build_gateway.sh --track all` 成功（Nuitka + PyInstaller）；
  - Tauri 构建：`cargo tauri build --no-bundle --no-sign` 成功，产物位于 `src-tauri/target/release/confluox-desktop`。
- 说明：本地 shell 为 zsh，验证时使用了 `python3`，且 `gateway[dev]` 需加引号防止 glob；CI workflow 中继续保留 `python -m ...` 以兼容三平台 runner。

### 7.3 Branch Protection 手工核验

- 远端查询：`gh api repos/Cocoblood9527/Confluox/branches/main/protection`；
- 结果：`Branch not protected (HTTP 404)`；
- 结论：当前仓库 `main` 尚未配置分支保护，需在 GitHub Settings 中手工绑定本 workflow 的检查状态后，才能形成“平台失败阻断合并”的强制门禁。

### 7.4 已知限制

- 目前仅 `macOS` 跑完整双轨 + tauri no-bundle 链路；
- `Ubuntu/Windows` 当前仅执行基础校验（gateway tests + frontend build + `gateway_artifact` Rust 测试）。
