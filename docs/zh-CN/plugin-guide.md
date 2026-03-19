# 插件指南

## 当前可用的插件模型

当前仓库支持两种插件类型：

- `type: "api"`：在网关进程内注册 FastAPI 路由（兼容现有插件，保持可用）
- `type: "worker"`：通过 `process_manager` 启动并登记受管后台进程

兼容性说明：

- 现有 `api` 插件无需修改即可继续工作。
- `worker` 当前只覆盖“受管进程启动/登记/关闭”，不等于已经提供进程沙箱隔离。
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
- 当前 enforcement 是 allowlist 启动门禁，不是完整的操作系统级沙箱。
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

当前行为：

- 插件发现阶段会按 host allowlist 校验 execution mode
- 激活阶段当前仅支持 `in_process`
- `out_of_process` 描述符在激活阶段会被显式拒绝并给出原因

启动时执行模式配置：

- `--allowed-api-execution-mode` / `CONFLUOX_ALLOWED_API_EXECUTION_MODES`：发现阶段可用模式白名单

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
- [English Plugin Guide](../en/plugin-guide.md)
