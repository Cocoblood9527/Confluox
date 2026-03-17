# 跨语言桌面桥接 MVP 执行导向 Spec

> 状态：已通过对话确认，待用户审核书面稿
> 日期：2026-03-17
> 上位文档：`docs/plan/跨语言桌面通用桥接框架 技术白皮书 V2.1.md`
> 下游文档：`docs/superpowers/plans/2025-03-17-mvp-cross-language-desktop-bridge.md`

## 1. 文档定位

本文件不是对白皮书 V2.1 的重写，也不是完整平台规格说明，而是本轮开发的执行导向 spec。

决策链如下：

1. 白皮书 V2.1 作为平台总 spec，定义长期架构方向与能力边界。
2. 本文件作为本轮 MVP 的执行导向 spec，明确本轮范围、关键契约、非目标与验收标准。
3. implementation plan 需要与本文件保持一致；若存在冲突，以本文件中的 MVP 决策为准，并对 plan 做必要修订。
4. 代码实现、验证、评审与收尾工作都以本文件为本轮依据。

## 2. 本轮目标

本轮交付一个可运行、可验证、可打包演进的最小闭环：

- Tauri 桌面宿主能够启动并托管 Python 本地网关；
- 前端能够通过宿主注入的地址与 token 调用网关；
- 网关能够挂载至少一个 API 插件；
- 启动、鉴权、关闭、宿主猝死回收、资源定位这些基础设施契约可被测试和验证。

本轮不是要交付完整插件平台，而是要建立一个后续能安全扩展的基础骨架。

## 3. 本轮范围

### 3.1 In Scope

- Tauri 宿主：
  - 启动 Python 网关 sidecar；
  - 注入 `data_dir`、`auth_token`、`ready_file`、`host_pid`、`allowed_origin`；
  - 启动前清理旧 `ready_file`；
  - 轮询结构化 `ready_file`；
  - 关闭时调用 shutdown API 并兜底终止 sidecar。
- Python 网关：
  - FastAPI 系统接口；
  - Bearer 鉴权；
  - 受限 CORS；
  - 宿主存活监控；
  - `ProcessManager`；
  - 资源路径解析；
  - API 插件加载。
- 插件模型：
  - 仅支持 `manifest.json + entry.py + setup(context)` 的 API 插件。
- 前端：
  - Vite + React SPA；
  - 统一 API 客户端；
  - 健康检查与示例插件状态展示。
- 打包：
  - 至少跑通 PyInstaller 轨道；
  - 打包前执行插件扫描；
  - Tauri 能在生产构建中启动冻结后的网关产物。

### 3.2 Out of Scope

- 完整服务型插件运行时；
- 完整 MCP 插件运行时；
- OpenAPI 聚合平台；
- SSE / WebSocket 全链路代理；
- 插件市场、插件管理界面；
- Next.js 作为默认前端方案；
- `Nuitka` 打包轨道；
- 云端能力、远程编排、多租户权限模型。

## 4. MVP 架构收缩

本轮采用四层最小实现：

1. Tauri / Rust 宿主层：
  负责 sidecar 生命周期、启动参数注入、ready 握手、关闭收尾。
2. Vite + React 前端层：
  只负责 UI 与调用，不承载后端逻辑。
3. Python / FastAPI 网关层：
  负责系统接口、鉴权、进程治理、配置注入、插件挂载。
4. 打包与分发层：
  负责 Python 网关冻结产物与 Tauri 集成。

插件层本轮只交付 API 插件，不把服务型插件或 MCP 插件并入同一实现批次。

## 5. 关键工程契约

以下契约是本轮 MVP 的硬约束，优先级高于代码组织偏好：

### 5.1 `ready_file` 是唯一可信启动信号

- 宿主只通过结构化 `ready_file` 判断 Python 网关是否就绪。
- 禁止解析 Uvicorn 日志来发现端口或判断启动成功。
- 仅当 `ready_file` 可解析为 JSON，且满足以下条件时，宿主才继续初始化：
  - `status == "ready"`
  - `pid` 与当前网关子进程 PID 一致
  - `port` 为有效端口
- 旧的 `ready_file` 必须在启动前清理。

### 5.2 鉴权默认开启，CORS 必须受限

- 网关 HTTP 路由默认都要求 `Authorization: Bearer <token>`。
- `/api/system/health` 不作为公开例外。
- CORS 只允许宿主注入的单一 `allowed_origin`。
- 明确禁止 `allowed_origin == "*"`。

### 5.3 正常关闭与异常退出都要统一收尾

- 正常关闭时，Tauri 拦截窗口关闭，先调用 `POST /api/system/shutdown`。
- 网关收到 shutdown 请求后，执行统一收尾逻辑并退出。
- 宿主异常退出时，网关通过 `host_pid` 监控感知宿主死亡，并执行同一套收尾逻辑。
- 收尾逻辑至少包括：
  - 删除 `ready_file`
  - 终止受托管子进程
  - 设置服务退出标记

### 5.4 子进程必须纳入 `ProcessManager`

- 网关与插件拉起的受托管子进程必须统一通过 `ProcessManager` 启动与终止。
- 禁止插件绕开 `ProcessManager` 自行管理长期子进程。
- 关闭、异常退出、未来插件扩展都必须复用统一进程治理路径。

### 5.5 资源路径与数据目录必须显式解析

- 运行时资源路径通过 `resource_resolver` 解析。
- 数据目录通过显式配置注入。
- 禁止依赖全局 `os.chdir(data_dir)` 这样的隐式副作用。
- 开发态与冻结态都必须具备一致可测试的路径行为。

## 6. 测试与验收策略

本轮测试采用分层验证：

### 6.1 Python 网关单元测试

优先覆盖以下模块：

- `config`
- `ready_file` 写入与握手辅助函数
- 系统路由
- 鉴权与 CORS
- `host_pid` 宿主存活监控
- `ProcessManager`
- `resource_resolver`
- 插件加载器

### 6.2 宿主与网关的集成验证

重点验证：

- 启动前旧 `ready_file` 清理；
- 结构化 ready JSON 轮询；
- 启动错误态上报；
- 窗口关闭触发 shutdown；
- 宿主异常退出时网关自收束。

### 6.3 前端端到端冒烟验证

最小要求：

- 前端能读取宿主注入的 `baseUrl` 与 `token`；
- 能调用 `/api/system/health`；
- 能调用示例 API 插件接口；
- 页面能显示成功或失败状态。

### 6.4 MVP 验收线

只有同时满足以下条件，本轮 MVP 才视为成立：

- 宿主能拉起网关并通过 `ready_file` 完成握手；
- 前端能带 Bearer token 成功访问网关；
- 至少一个 API 插件完成挂载并可调用；
- 正常关闭与宿主猝死都能完成进程回收；
- 资源与数据目录在开发态和至少一条冻结态路径上行为正确；
- PyInstaller 打包链路可用，并被 Tauri 正确集成。

## 7. 对现有 implementation plan 的要求

现有 plan 总体方向可继续使用，但必须满足以下要求：

- 保持本轮只实现 API 插件，不把服务型插件与 MCP 插件混入当前任务集；
- 把关键工程契约全部落实为可测试、可验证的步骤，而不是只停留在描述层；
- 允许对现有 plan 做必要修订，以消除与本 spec 的冲突；
- 执行阶段默认采用 `subagent-driven-development`，若受环境约束无法使用，再退回单会话执行；
- 执行前需补齐 Git 仓库与隔离工作区前置条件。

## 8. 后续流程

本文件经用户审核确认后，进入以下步骤：

1. 校对并修订 implementation plan；
2. 初始化 Git 仓库并准备隔离工作区；
3. 进入实现执行流程；
4. 阶段性验证与评审；
5. 完成收尾与交付确认。

## 9. Phase 2 预留决策

- `Nuitka` 打包轨道不属于本轮 MVP 交付。
- 在 `PyInstaller` 轨道、插件扫描、冻结态资源解析与 Tauri 集成稳定之后，再进入 Phase 2 评估并实现 `Nuitka`。
- `Nuitka` 的引入目标是补充性能与产物保护选项，而不是替代本轮 MVP 的默认打包链路。
