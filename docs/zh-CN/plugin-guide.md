# 插件指南

## 当前可用的插件模型

当前仓库支持两种插件类型：

- `type: "api"`：在网关进程内注册 FastAPI 路由（兼容现有插件，保持可用）
- `type: "worker"`：通过 `process_manager` 启动并登记受管后台进程

兼容性说明：

- 现有 `api` 插件无需修改即可继续工作。
- `worker` 现在在 POSIX 平台上提供了最小 OS 级硬化路径（基于 `sandbox_profile`）。
- `api` 插件加载现在带有信任策略：不受信任来源默认会被拒绝，除非显式信任。

## 插件目录结构

```text
plugins/
  your_plugin/
    manifest.json
    entry.py
```

## Manifest

最小示例：

```json
{
  "type": "api",
  "entry": "entry:setup",
  "name": "your_plugin"
}
```

`api` 插件最常用字段：

- `type`：`api`
- `entry`：格式为 `module:function`
- `name`：插件显示名称

`worker` 插件最小示例：

```json
{
  "type": "worker",
  "name": "example_worker",
  "runtime": "python",
  "permissions": {
    "fs": ["read:/tmp"],
    "network": ["loopback"]
  },
  "command": ["python3", "-m", "worker.main"]
}
```

`worker` 字段说明：

- `type`：`worker`
- `runtime`：运行时标签（文档/元数据用途）
- `permissions`：worker 启动前会强制执行的权限声明
- `sandbox_profile`：可选的 worker 沙箱 profile 声明（如 `restricted`、`strict`）
- `command`：由网关通过 `process_manager` 启动的命令数组

注意：

- `permissions` 现在会在启动前执行校验，违反策略会拒绝启动 worker 进程。
- `sandbox_profile` 也会在 spawn 前校验，不在允许列表内会被拒绝并返回策略原因。
- `sandbox_profile=restricted` 依赖主机具备 POSIX preexec 与 `RLIMIT_CORE` capability；满足时会在 `exec` 前应用 `RLIMIT_CORE=0`（禁用 core dump）。
- `sandbox_profile=strict` 需要更严格 capability（`restricted` 基线 + `RLIMIT_NOFILE` + seccomp 支持），并在上述基础上施加 open files 上限。
- 缺失必需 capability 会 fail-closed 并返回结构化拒绝（`sandbox_capability_missing`）；seccomp 运行时不可用会返回 `sandbox_runtime_not_supported`。
- 网关不会自动把 `strict` 降级为 `restricted`，需要在 manifest 中按主机能力显式声明回退策略。
- 当前 enforcement 是 allowlist + 轻量 OS 级硬化，不是完整内核级沙箱策略。
- `worker` 不会自动暴露 API 路由；它是后台受管进程模型。

## API 信任策略

`api` 插件在发现阶段会执行信任检查：

- 仓库 `plugins/` 根目录下的插件默认信任
- 不在受信任根路径内的插件视为不受信任，默认拒绝
- 对不受信任来源，只能通过显式信任配置放行

启动时信任配置：

- `--trusted-api-plugin-root` / `CONFLUOX_TRUSTED_API_PLUGIN_ROOTS`：新增受信任根路径
- `--trusted-api-plugin` / `CONFLUOX_TRUSTED_API_PLUGINS`：按插件名显式信任（用于不受信任来源）

## API 执行模式策略

`api` manifest 现在可选声明 `execution_mode`：

- `in_process`（默认）：当前支持的执行模式
- `out_of_process`：为后续隔离路径预留的策略契约模式

当 `execution_mode=out_of_process` 时，manifest 必须提供 `command`：

- `command`：启动插件进程的命令数组

当前行为：

- 插件发现阶段会按 host allowlist 校验 execution mode
- 启动阶段仅做 descriptor 发现；API 插件默认采用“首个命中请求再激活”的 lazy activation
- 首次访问 `/api/<plugin_name>` 时触发激活（`in_process` 执行 setup；`out_of_process` 拉起进程并做健康检查握手）
- 请求会代理到 `/api/<plugin_name>` 前缀
- 启动失败会返回显式诊断（`api_oop_boot_timeout`、`api_oop_process_exited`）
- 代理运行时失败会返回结构化 `502` 响应（`api_oop_upstream_unavailable`）

启动时执行模式配置：

- `--allowed-api-execution-mode` / `CONFLUOX_ALLOWED_API_EXECUTION_MODES`：发现阶段可用模式白名单
- `--api-out-of-process-boot-timeout-seconds` / `CONFLUOX_API_OOP_BOOT_TIMEOUT_SECONDS`：out-of-process 启动超时配置

Out-of-process 插件运行时契约：

- host 注入 `CONFLUOX_PLUGIN_PORT`
- host 注入 `CONFLUOX_PLUGIN_PREFIX`
- host 注入 `CONFLUOX_PLUGIN_AUTH_TOKEN`
- 插件必须提供 `GET /__confluox/health`，ready 时返回 `200`
- 建议插件对健康检查和代理请求统一校验 `X-Confluox-Plugin-Auth`

安全与韧性控制项：

- `--api-out-of-process-max-active-plugins` / `CONFLUOX_API_OOP_MAX_ACTIVE_PLUGINS`：同时激活的 out-of-process API 插件上限
- `--api-out-of-process-circuit-failure-threshold` / `CONFLUOX_API_OOP_CIRCUIT_FAILURE_THRESHOLD`：触发熔断前的连续失败阈值
- `--api-out-of-process-circuit-open-seconds` / `CONFLUOX_API_OOP_CIRCUIT_OPEN_SECONDS`：熔断打开时长

新增诊断码：

- 鉴权握手失败：`api_oop_auth_failed`
- 激活配额超限：`api_oop_quota_exceeded`
- 熔断开启回退：`api_oop_circuit_open`
- 激活状态快照端点：`GET /api/system/plugin-activation`
- 激活失败状态会保留，并以稳定 `error_code` / `error_message` 对外可见

预热建议：

- 如果你的场景需要在用户流量前提前热启动插件，可在启动后主动请求插件健康或业务路由（例如 `GET /api/<plugin_name>`）
- 预热是可选项；默认契约仍是首请求 lazy activation

## 入口函数

入口模块需要暴露一个 `setup(context)` 函数。

示例：

```python
from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/your-plugin")

    @router.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    context.app.include_router(router)
```

## `context` 里有什么

插件上下文当前会提供：

- `app`：FastAPI 应用实例
- `data_dir`：由桌面宿主注入的数据目录
- `auth`：本地网关使用的 bearer token
- `process_manager`：子进程管理辅助对象
- `resource_resolver`：打包资源定位辅助函数

## 推荐的插件约束

- 路由尽量稳定、明确
- 不要依赖全局当前工作目录
- 插件数据写到 `context.data_dir`
- 打包资源通过框架提供的解析器定位
- 把插件当成本地后端能力，而不是第二个应用宿主
- `worker` 进程应可被优雅终止，避免依赖不可控的守护行为

## 前端怎么调用

前端通过统一 API 客户端访问插件。

示例：

```ts
const result = await apiGet('/api/your-plugin/ping')
```

这个客户端会自动解析网关地址，并在请求里附带 bearer token。

## 推荐开发流程

1. 在 `plugins/` 下新建插件目录
2. 添加 `manifest.json`
3. 实现 `entry.py`
4. 运行前端和桌面宿主
5. 先确认新路由能通
6. 再补 UI

## 相关文档

- [快速开始](quick-start.md)
- [开源项目接入指南](integration-guide.md)
- [实例说明](实例说明.md)
- [English Plugin Guide](../en/plugin-guide.md)
