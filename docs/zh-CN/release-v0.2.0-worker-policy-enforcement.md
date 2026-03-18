# Confluox v0.2.0：Worker 权限强制与 API 信任策略

发布日期：2026-03-19  
标签：`v0.2.0-worker-policy-enforcement`

## 关键更新

- worker 插件 `permissions` 从“仅元数据”升级为“启动前强制校验”。
- worker 启动前会执行 allowlist 策略，不满足策略将拒绝拉起进程。
- 不受信任来源的 `api` 插件默认拒绝加载。
- 可通过启动配置显式扩展 API 插件信任范围。

## 变更明细

### 1. Worker 权限策略已落地执行

- 新增权限声明解析、归一化与策略评估原语。
- 若权限声明超出宿主 allowlist，worker 不会 spawn。
- 拒绝原因会通过结构化 policy violation 暴露。

### 2. API 插件默认信任策略改为“默认拒绝不受信来源”

- API 插件发现阶段会标记 descriptor 的 trust source。
- 仓库 `plugins/` 根目录下插件仍默认信任。
- 不在受信任根路径内的插件，若未显式信任则拒绝加载。

### 3. 新增信任配置入口

- CLI：`--trusted-api-plugin-root`（可重复）
- CLI：`--trusted-api-plugin`（可重复）
- 环境变量：`CONFLUOX_TRUSTED_API_PLUGIN_ROOTS`（逗号分隔）
- 环境变量：`CONFLUOX_TRUSTED_API_PLUGINS`（逗号分隔）

## 验证快照

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests -q` -> `57 passed`
- `cargo test --manifest-path src-tauri/Cargo.toml -- --nocapture` -> `8 passed, 0 failed`
- `cd frontend && npm run build` -> 构建成功

## 当前范围边界

本版本未包含：

- 操作系统级 worker 沙箱隔离
- 启动门禁之外更细粒度的 syscall/network/file 强制
- API 插件迁移到进程外执行
