# 插件指南

## 当前可用的插件模型

当前仓库里最完整、最成熟的是 API 插件模型。

网关会扫描 `plugins/` 目录，读取每个 `manifest.json`，并加载其中 `type` 为 `api` 的插件。

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

当前 loader 实际使用的字段有：

- `type`：必须是 `api`
- `entry`：格式为 `module:function`
- `name`：插件显示名称

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
