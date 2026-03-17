# Phase 2 Nuitka 双轨打包执行导向 Spec

> 状态：实现已完成（本地验证通过，待提交）
> 日期：2026-03-17
> 上位文档：`docs/superpowers/specs/2026-03-17-mvp-desktop-bridge-design.md`
> 下游文档：`docs/superpowers/plans/2026-03-17-phase2-nuitka-dual-track-plan.md`

## 1. 文档定位

本文件是 Phase 2 的执行导向 spec，目标是在不破坏现有 PyInstaller 链路的前提下，引入 Nuitka 打包轨道并接入桌面运行时选择逻辑。

本文件聚焦本轮“可执行、可验证、可回退”的工程契约，不重写 MVP 既有设计。

## 2. 本轮目标

本轮交付目标：

- 保留 PyInstaller 轨道并继续可用；
- 新增 Nuitka 轨道（本轮仅 macOS）；
- 建立统一产物契约，让 Tauri 运行时通过元数据选择轨道；
- 运行时默认优先 Nuitka，失败时回退 PyInstaller；
- 双轨不可用时给出可定位错误。

## 3. 范围定义

### 3.1 In Scope

- 网关打包双轨：
  - `PyInstaller` 轨道标准化为契约输出；
  - `Nuitka` 轨道新增并输出同构元数据；
- Tauri 运行时：
  - 从“硬编码路径猜测”收敛到“读取产物元数据决策”；
  - 选择顺序固定：Nuitka -> PyInstaller；
- 构建脚本：
  - 统一入口 + 分轨脚本；
  - 支持 `--track` 与 `--prefer`；
- 测试与验收：
  - 元数据与选择逻辑单测；
  - 双轨构建与回退链路验收。

### 3.2 Out of Scope

- Windows/Linux Nuitka 实测交付；
- CI 矩阵与性能基准；
- 前端界面层的轨道切换开关；
- 替换 PyInstaller 为唯一默认轨道。

## 4. 关键工程契约

### 4.1 统一产物目录契约

- `dist/gateway/nuitka/`
- `dist/gateway/pyinstaller/`

每条轨道都必须生成 `gateway-artifact.json`，路径分别为：

- `dist/gateway/nuitka/gateway-artifact.json`
- `dist/gateway/pyinstaller/gateway-artifact.json`

### 4.2 统一元数据字段契约

`gateway-artifact.json` 至少包含：

- `track`: `nuitka` 或 `pyinstaller`
- `platform`: 本轮固定 `darwin-arm64`
- `entry`: 可执行入口相对路径
- `resources_dir`: 资源根相对路径
- `version`: 网关版本
- `built_at`: ISO8601 时间戳

### 4.3 运行时选择契约

- Tauri 运行时只认元数据，不认打包器细节；
- 默认顺序：先尝试 Nuitka，再尝试 PyInstaller；
- 任一轨道元数据存在且可解析，且 `entry` 存在即可启动；
- 运行时不读取额外的“preferred track”文件或构建参数作为选择依据；
- 双轨都不可用时，报错必须包含已检查路径与失败原因。

### 4.4 回退契约

- `--track all`：至少一条轨道成功则整体成功；
- `--track nuitka`：Nuitka 失败即失败；
- 发布链路允许 Nuitka 失败后回退 PyInstaller，不得影响已稳定 MVP 主链路。

## 5. 构建流程与脚本边界

### 5.1 统一入口

`gateway/scripts/build_gateway.sh` 作为总入口，支持：

- `--track nuitka|pyinstaller|all`（默认 `all`）
- `--prefer nuitka|pyinstaller`（默认 `nuitka`，仅用于构建顺序、日志与验收优先级，不改变运行时固定选择顺序）

### 5.2 分轨脚本

- `gateway/scripts/build_gateway_pyinstaller.sh`
- `gateway/scripts/build_gateway_nuitka.sh`

两者共享插件扫描结果（`scan_plugins.py`），避免重复扫描与参数漂移。

### 5.3 Tauri 资源与运行时

- `tauri.conf.json` 需打包双轨资源；
- Rust 端读取 `gateway-artifact.json` 进行选择；
- Rust 端选择顺序固定为“Nuitka 优先，PyInstaller 兜底”；
- 不再依赖硬编码产物名称作为主逻辑。

## 6. 测试与验收

### 6.1 单元测试

- 网关侧：元数据生成与字段校验测试；
- 宿主侧：轨道选择逻辑测试（Nuitka 优先、PyInstaller 回退、双失败报错）。

### 6.2 构建验收命令（macOS）

- `./gateway/scripts/build_gateway.sh --track pyinstaller`
- `./gateway/scripts/build_gateway.sh --track nuitka`
- `./gateway/scripts/build_gateway.sh --track all`

每条命令执行后，都要核验对应轨道 `gateway-artifact.json`。

### 6.3 集成验收

- `cargo tauri build --no-bundle --no-sign` 通过；
- 资源目录包含双轨产物；
- 启动日志或状态输出可确认“优先 Nuitka”的实际选择结果。

### 6.4 回退验收

- 临时移除 Nuitka 元数据，确认自动回退 PyInstaller；
- 临时移除双轨元数据，确认报错包含 checked paths。

### 6.5 通过线

只有同时满足以下条件才视为本轮完成：

- 双轨可独立构建（macOS）；
- 运行时选择契约与回退契约成立；
- PyInstaller 既有能力不回归（插件加载、ready/shutdown 主链路保持可用）。

## 7. 实施原则

- 先契约后实现：先统一目录与元数据，再接入运行时选择；
- 不破坏主链路：本轮新增不得影响现有 PyInstaller 可用性；
- 可观察、可定位：失败信息必须直接可用于排查。

## 8. 实现结果与执行证据（2026-03-17）

### 8.1 已完成实现

- 网关侧新增产物契约模块：`gateway/gateway/artifact_contract.py`
- 网关侧新增契约单测：`gateway/tests/test_artifact_contract.py`
- 构建入口拆分为双轨：
  - `gateway/scripts/build_gateway.sh`
  - `gateway/scripts/build_gateway_pyinstaller.sh`
  - `gateway/scripts/build_gateway_nuitka.sh`
- 构建策略与参数测试：`gateway/tests/test_build_gateway_cli.py`
- Tauri 侧新增轨道选择模块：`src-tauri/src/gateway_artifact.rs`
- 运行时切换到元数据选择：`src-tauri/src/gateway.rs`
- 模块注册：`src-tauri/src/lib.rs`
- 资源映射改为双轨目录：`src-tauri/tauri.conf.json`

### 8.2 关键验证命令（本地实测）

以下命令在本地执行通过（exit code = 0）：

- `cd gateway && python3 -m pytest tests -q`
- `cd frontend && npm run build`
- `cargo build --manifest-path src-tauri/Cargo.toml`
- `cd gateway && ./scripts/build_gateway.sh --track pyinstaller`
- `cd gateway && ./scripts/build_gateway.sh --track nuitka`
- `cd gateway && ./scripts/build_gateway.sh --track all`
- `cargo test --manifest-path src-tauri/Cargo.toml gateway_artifact -- --nocapture`
- `cargo tauri build --no-bundle --no-sign`
- `cargo tauri build --no-sign`

### 8.3 产物与资源核验

- 本地产物元数据存在：
  - `dist/gateway/nuitka/gateway-artifact.json`
  - `dist/gateway/pyinstaller/gateway-artifact.json`
- Bundle 内元数据存在：
  - `.../Contents/Resources/gateway/nuitka/gateway-artifact.json`
  - `.../Contents/Resources/gateway/pyinstaller/gateway-artifact.json`

### 8.4 回退契约核验

- `gateway_artifact` 单测已覆盖并通过：
  - 双轨都存在时优先 `nuitka`
  - `nuitka` 缺失时回退 `pyinstaller`
  - 双轨不可用时返回包含 checked paths 的诊断错误

### 8.5 已知说明

- Nuitka 首次构建会下载/初始化 ccache，耗时显著高于后续构建。
- 为避免将 Nuitka 中间编译目录打入资源，构建脚本已启用 `--remove-output`。
