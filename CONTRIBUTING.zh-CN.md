# 参与 Confluox

[English](CONTRIBUTING.md)

感谢你对 Confluox 的关注。

Confluox 目前仍处于早期阶段，所以最有价值的贡献通常是聚焦、务实、易验证的改进，而不是大范围重写。文档完善、开发体验优化、插件示例、网关稳定性改进，以及打包流程增强，都是当前非常欢迎的方向。

## 在开始贡献之前

在提交 issue 或 pull request 之前，建议先阅读：

- [README.md](README.md)
- [快速开始](docs/zh-CN/quick-start.md)
- [插件指南](docs/zh-CN/plugin-guide.md)
- [开源项目接入指南](docs/zh-CN/integration-guide.md)

这样可以让讨论更贴近当前架构和项目范围。

## 本地开发环境

### 前置依赖

- Python 3.10 或更高版本
- Node.js 20 或更高版本
- Rust toolchain
- Tauri CLI

### 安装依赖

```bash
python -m pip install -U pip
python -m pip install -e 'gateway[dev]'
cd frontend && npm ci
cargo install tauri-cli --version "^2" --locked
```

### 本地运行项目

终端 1：

```bash
cd frontend
npm run dev
```

终端 2：

```bash
cargo tauri dev
```

### 常用验证命令

运行 gateway 测试：

```bash
cd gateway
python -m pytest tests -q
```

构建 gateway 产物：

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

## 适合作为首个贡献的方向

比较适合当前阶段的贡献包括：

- 文档补充和说明澄清
- 用户向文档的中英文同步
- 插件示例和接入示例完善
- gateway 稳定性或错误处理改进
- 打包和构建流程修复
- 与当前风格一致的小型前端体验优化

除非维护者明确提出，否则不建议一开始就做大范围架构重写。

## Issue 指南

如果你要提交 bug，请尽量包含：

- 你原本预期会发生什么
- 实际发生了什么
- 复现步骤
- 有帮助的话附上日志或截图
- 如果相关，也请说明环境信息

如果你要提功能建议，请优先说明：

- 使用场景
- 想解决的问题
- 重要约束或取舍

通常这比直接给出完整实现方案更有帮助。

## Pull Request 指南

请尽量让 PR 保持聚焦、易于评审。

一个好的 PR 通常应该说明：

- 改了什么
- 为什么要改
- 你做了哪些验证
- 如果行为、安装流程或协作方式变了，是否同步更新了文档

如果可以的话，也建议：

- 尽量提交较小、边界清晰的 PR
- 不要在同一个 PR 里混入无关重构
- 如果有刻意留到后续再做的内容，请明确写出来

## 文档与语言策略

Confluox 当前采用英文优先的 GitHub 文档策略。

目前的约定是：

- `README.md` 是主要仓库入口
- 面向用户的上手文档应尽量提供中文镜像版
- 如果你修改了公开的安装、使用、接入文档，请尽量同步更新对应的中文或英文版本
- 如果同一个 PR 里暂时无法完整补齐翻译，请明确说明，而不要让它处于不清楚的状态

并不是每一个很小的内部文案调整都要求绝对同步，但面向新用户的入口文档不应长期失配。

## 范围与边界

请结合当前项目阶段来贡献：

- 目前最完整的接入路径仍然是 API 插件
- 规划文档里提到的插件模型，并不代表现在都已经完整实现
- Confluox 目前还不是“任意大型第三方系统零成本桌面化”的工具
- 除非维护者明确提出，不建议主动补很多大型治理或流程文档

如果你不确定一个想法是否适合当前阶段，先开一个 issue 讨论会是很好的方式。
