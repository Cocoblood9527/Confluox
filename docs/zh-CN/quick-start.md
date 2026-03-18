# 快速开始

## 你实际启动了什么

在开发态，Confluox 会把三部分一起跑起来：

- 一个运行在 `http://localhost:1420` 的 Vite 前端
- 一个 Tauri 桌面宿主
- 一个由桌面宿主拉起的 Python 网关进程

桌面宿主会先启动网关，等待 ready file 写入，再把网关地址和鉴权 token 暴露给前端。

## 前置依赖

- Python 3.10 或更高版本
- Node.js 20 或更高版本
- Rust toolchain
- Tauri CLI

## 安装依赖

### Python 网关

```bash
python -m pip install -U pip
python -m pip install -e 'gateway[dev]'
```

### 前端

```bash
cd frontend
npm ci
```

### Tauri CLI

```bash
cargo install tauri-cli --version "^2" --locked
```

## 开发态运行

先启动前端：

```bash
cd frontend
npm run dev
```

再启动桌面应用：

```bash
cargo tauri dev
```

如果一切正常，桌面窗口里应该能看到：

- gateway base URL
- auth token
- gateway health 状态
- example plugin 返回值

## 开发态运行原理

- 前端由 Vite 在 `1420` 端口提供服务
- Tauri 在开发态连接这个 URL
- Rust 宿主启动 `python -m gateway.main`
- Python 网关绑定一个随机 localhost 端口
- 网关把实际端口写进 ready file
- Rust 读取 ready file，再把最终连接信息交给前端

## 构建网关产物

做生产打包前，先构建网关产物：

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

这个脚本会准备 `dist/gateway`，供 Tauri 在 bundle 阶段作为资源打包。

## 构建桌面应用

当前端产物和网关产物都准备好之后：

```bash
cd frontend
npm run build
cd ..
cargo tauri build
```

## 相关文档

- [插件指南](plugin-guide.md)
- [开源项目接入指南](integration-guide.md)
- [English Quick Start](../en/quick-start.md)
