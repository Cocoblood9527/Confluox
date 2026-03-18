# Confluox

[English](README.md)

Confluox 是一个桌面桥接框架，用来把本地能力组织成一个有统一宿主、统一网关、统一插件入口的桌面产品。

它目前由这几层组成：

- `Tauri + Rust` 作为桌面宿主
- `Python + FastAPI` 作为本地网关
- `React + Vite` 作为前端界面
- `plugins/` 作为主要扩展入口

## 适合谁使用

Confluox 适合下面这类场景：

- 给 Python 能力包一层桌面应用
- 把本地工具、脚本、小型服务接入统一桌面壳
- 把可适配的开源项目接进一个受控的桌面宿主
- 统一管理启动、关闭、鉴权和打包流程

## 不适合哪些场景

如果你的目标更接近下面这些情况，Confluox 大概率不是最合适的方案：

- 希望任何大型开源系统都能零改造直接桌面化
- 需要的是云端编排平台，而不是本地桌面宿主
- 希望它立刻替代你现有应用的全部运行时体系

## 架构概览

```text
React + Vite 前端
        |
        | invoke + fetch
        v
Tauri 桌面宿主
        |
        | 启动 / 关闭 / 注入运行时配置
        v
Python 本地网关
        |
        | 挂载路由 / 管理鉴权 / 生命周期
        v
API 插件 / 适配器 / 受管控的本地进程
```

当前仓库里已经落地的关键链路有：

- 桌面宿主启动网关，并通过结构化 ready file 等待就绪
- 网关绑定本地端口，启用 bearer token 鉴权，并加载 API 插件
- 前端从 Tauri 获取网关连接信息，再通过统一客户端访问本地 API
- 插件统一挂在网关后面，这样桌面宿主和前端只需要面对一个稳定的集成入口

## 快速开始

### 前置依赖

- Python 3.10+
- Node.js 20+
- Rust toolchain
- Tauri CLI

### 安装依赖

```bash
python -m pip install -U pip
python -m pip install -e 'gateway[dev]'
cd frontend && npm ci
cargo install tauri-cli --version "^2" --locked
```

如果你在用 Git worktree，请在当前 worktree 里执行可编辑安装。切换 worktree 后，`confluox-gateway` 可能还指向旧目录，这时建议重新执行一次 `gateway[dev]` 安装。

### 启动本地开发环境

终端 1：

```bash
cd frontend
npm run dev
```

终端 2：

```bash
cargo tauri dev
```

当前前端开发服务器固定使用 `http://localhost:1420`，桌面宿主在开发态会连接这个地址。

## 仓库结构

```text
frontend/     React + Vite 前端
gateway/      Python 网关和构建脚本
src-tauri/    Tauri 桌面宿主
plugins/      插件清单和入口
dist/         桌面打包时使用的网关产物
docs/         设计文档和使用指南
```

## 如何写第一个插件

当前最简单、最成熟的接入方式是 API 插件。

先创建一个插件目录：

```text
plugins/
  todo_api/
    manifest.json
    entry.py
```

示例 `manifest.json`：

```json
{
  "type": "api",
  "entry": "entry:setup",
  "name": "todo_api"
}
```

示例 `entry.py`：

```python
from fastapi import APIRouter


def setup(context) -> None:
    router = APIRouter(prefix="/api/todo")

    @router.get("/items")
    def list_items() -> dict[str, object]:
        return {"items": [], "data_dir": context.data_dir}

    context.app.include_router(router)
```

然后前端通过统一 API 客户端调用它：

```ts
const result = await apiGet('/api/todo/items')
```

## 如何接入一个开源项目

更合适的心智模型是：把 Confluox 当成桥接框架，而不是任意项目零改造桌面化工具。

- 轻量 FastAPI 或路由式 Python 项目最适合，优先改造成 API 插件
- CLI 工具或本地服务通常需要一层 adapter，并交给框架管理子进程
- 大型完整系统不建议直接硬塞进主网关，更适合做隔离式适配或代理接入

可以简单理解为：

- 低成本路径：API 插件
- 中等成本路径：可适配的第三方 Python 项目
- 较高成本路径：大型服务型系统

## 打包

开发态会直接从 Python 启动网关。

生产态则依赖 `dist/gateway` 下的网关产物，并把这些产物打进 Tauri bundle 资源里。

先构建网关产物：

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

再构建桌面应用：

```bash
cargo tauri build
```

## 文档

- [快速开始](docs/zh-CN/quick-start.md)
- [插件指南](docs/zh-CN/plugin-guide.md)
- [开源项目接入指南](docs/zh-CN/integration-guide.md)
- [架构审查报告](docs/zh-CN/architecture-review.md)
- [参与贡献](CONTRIBUTING.zh-CN.md)
- [English README](README.md)

## 当前状态

Confluox 目前仍然是早期阶段框架。现阶段最完整、最适合直接使用的是 API 插件路径；更广义的适配器和服务型接入能力还在持续演进中。

## 许可证

Confluox 使用 [MIT License](LICENSE)。
