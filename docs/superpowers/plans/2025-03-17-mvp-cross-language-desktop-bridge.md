# 跨语言桌面通用桥接框架 MVP 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现《跨语言桌面通用桥接框架 技术白皮书 V2.1》定义的 MVP：Tauri 桌面宿主 + Python 本地网关 + API 插件模型 + 统一鉴权与优雅停机 + Vite+React 前端，形成可运行、可打包的跨语言桌面桥接最小闭环，并补齐宿主存活监控、结构化 ready 握手与打包约束。

**Architecture:** 四层结构：1) Tauri 宿主负责启动 Python 网关 sidecar、注入 `data_dir/auth_token/ready_file/host_pid/allowed_origin`、启动前清理旧 ready_file、轮询结构化 ready_file 获取端口、暴露给前端、拦截关闭并调用 shutdown API；2) 前端 Vite+React SPA 仅做 UI，通过统一 SDK 调用网关；3) Python 网关 FastAPI 负责系统接口、API 插件挂载、Bearer 鉴权与受限 CORS、宿主存活监控、ProcessManager、资源解析与数据目录注入；4) 端口发现固定采用方案 A：Python 进程内预绑定 socket，FastAPI 生命周期确认启动后原子写入 `status=ready` 的 ready_file，禁止解析 Uvicorn 日志。优雅停机、子进程治理与宿主猝死收束为强制契约。

**Tech Stack:** Rust + Tauri 2.x, Python 3.10+, FastAPI + Uvicorn, Vite + React + TypeScript, PyInstaller（MVP 首选且唯一要求落地的打包轨道）+ 预构建扫描脚本，Nuitka 作为 Phase 2 打包轨道保留。

**Spec:** `docs/plan/跨语言桌面通用桥接框架 技术白皮书 V2.1.md`

---

## 文件与目录结构（约定后不再分散说明）

```
confluox/
├── src-tauri/                    # Tauri 桌面宿主
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   └── src/
│       ├── main.rs
│       ├── lib.rs
│       └── gateway.rs            # 启动/轮询/关闭网关进程
├── gateway/                       # Python 本地网关
│   ├── pyproject.toml
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── main.py               # 入口、参数解析、端口绑定、生命周期、ready_file、uvicorn
│   │   ├── config.py             # 配置与环境（data_dir, auth_token, ready_file, host_pid, allowed_origin）
│   │   ├── auth.py               # Bearer 鉴权中间件 + CORS
│   │   ├── host_liveness.py      # host_pid 轮询与宿主猝死收束
│   │   ├── process_manager.py    # 子进程托管与 terminate_all
│   │   ├── resource_resolver.py  # get_resource_path(relative_path)
│   │   ├── plugin_loader.py      # 扫描 manifest + entry.setup(context)
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── system.py         # /api/system/health, shutdown 等
│   ├── tests/
│   │   ├── test_config.py
│   │   ├── test_main_ready.py
│   │   ├── test_auth.py
│   │   ├── test_host_liveness.py
│   │   ├── test_process_manager.py
│   │   ├── test_resource_resolver.py
│   │   ├── test_plugin_loader.py
│   │   └── test_system_routes.py
│   └── scripts/
│       ├── scan_plugins.py       # 预构建扫描，生成 hidden-import / data 收集结果
│       └── build_gateway.sh      # 调用扫描器 + PyInstaller 打包
├── plugins/
│   └── example_api/
│       ├── manifest.json
│       └── entry.py              # setup(context) 注册 APIRouter
├── frontend/                     # Vite + React SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       └── api/                  # 统一 SDK 封装（baseURL + Authorization）
│           └── client.ts
├── docs/
│   ├── plan/                     # 已有白皮书
│   └── superpowers/
│       └── plans/                # 本计划
└── .agentdocs/                   # 可选，项目约束与记忆
```

以上结构在后续任务中按「Create/Modify」精确引用；测试与实现严格 TDD，每步可单独运行与提交。

---

## Phase 1：项目骨架与 Tauri 最小宿主

### Task 1: 仓库与 Tauri 应用骨架

**Files:**
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/build.rs`
- Create: `src-tauri/src/main.rs`
- Create: `src-tauri/src/lib.rs`

- [ ] **Step 1: 创建 Tauri 应用**

使用 Tauri 2.x 官方脚手架或手动创建：`src-tauri/Cargo.toml` 依赖 `tauri`, `tauri-build`；`tauri.conf.json` 中 `identifier` 设为 `com.confluox.desktop`，`build.distDir` 暂指向 `../frontend/dist`（后续前端产出）。

- [ ] **Step 2: 验证 Tauri 构建**

在项目根目录执行（需已安装 Rust + Tauri CLI）：
`cargo build --manifest-path src-tauri/Cargo.toml`
预期：编译通过。

- [ ] **Step 3: Commit**

```bash
git add src-tauri/
git commit -m "chore: add Tauri 2.x desktop host skeleton"
```

---

### Task 2: 前端 Vite + React 骨架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 初始化 Vite + React + TypeScript**

`npm create vite@latest frontend -- --template react-ts`（或等价命令），确保产物为 SPA，输出目录 `dist`。

- [ ] **Step 2: 配置 Tauri 加载 dist**

确认 `src-tauri/tauri.conf.json` 中 `build.distDir` 为 `../frontend/dist`；运行 `npm run build` 于 frontend，再运行 Tauri 应用，预期：窗口加载前端页面。

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "chore: add Vite + React SPA skeleton for Tauri"
```

---

## Phase 2：Python 网关核心（无插件）

### Task 3: 网关项目与配置模型

**Files:**
- Create: `gateway/pyproject.toml`
- Create: `gateway/gateway/__init__.py`
- Create: `gateway/gateway/config.py`
- Test: `gateway/tests/test_config.py`

- [ ] **Step 1: 编写失败测试（config 从环境/参数加载）**

在 `gateway/tests/test_config.py` 中：从环境变量或 CLI 参数读取 `data_dir`, `auth_token`, `ready_file`, `host_pid`, `allowed_origin`；断言 `Config` 对象包含这些字段且类型正确；若 `allowed_origin == "*"` 则抛错。

- [ ] **Step 2: 运行测试确认失败**

`cd gateway && python -m pytest tests/test_config.py -v`
预期：FAIL（无 config 模块或未实现）。

- [ ] **Step 3: 实现 config**

在 `gateway/gateway/config.py` 定义 `Config`（dataclass 或 Pydantic），从 `argparse` 或 `os.environ` 读取：`--data-dir`, `--auth-token`, `--ready-file`, `--host-pid`, `--allowed-origin`；对 `allowed_origin="*"` 直接拒绝；禁止在此处做 `os.chdir(data_dir)`。

- [ ] **Step 4: 运行测试通过**

`python -m pytest tests/test_config.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): add config model for data_dir, auth, ready_file, host_pid"
```

---

### Task 4: 端口绑定与 ready_file 辅助函数

**Files:**
- Create: `gateway/gateway/main.py`（仅端口与 ready 逻辑）
- Test: `gateway/tests/test_main_ready.py`

- [ ] **Step 1: 编写失败测试（端口绑定 + ready 文件）**

测试：在临时目录创建 ready_file 路径；调用“绑定 `127.0.0.1:0`”辅助函数拿到 socket 与端口；再调用“原子写 ready 文件”辅助函数；断言 ready 文件存在且内容为 JSON，至少包含 `status`, `port`, `pid`, `version`；当 `status != "ready"` 时宿主不得视为可用；端口在 1-65535 之间。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_main_ready.py -v`
预期：FAIL。

- [ ] **Step 3: 实现端口绑定与 ready 写入**

在 `main.py` 中提供可被测试调用的辅助函数：1) 创建 `socket.socket` 绑定 `127.0.0.1:0` 并返回 socket 与端口；2) 原子写入 ready_file（先写临时文件再 rename）。ready payload 固定结构为 `{"status":"ready","port":port,"pid":os.getpid(),"version":"0.1.0"}`；错误态预留 `{"status":"error","message":"..."}`。本步不启动 Uvicorn，只沉淀握手协议与文件写入原语。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_main_ready.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): bind port and write structured ready_file for handshake"
```

---

### Task 5: FastAPI 应用与 Uvicorn 程序化启动

**Files:**
- Modify: `gateway/gateway/main.py`
- Create: `gateway/gateway/routes/__init__.py`
- Create: `gateway/gateway/routes/system.py`
- Test: `gateway/tests/test_system_routes.py`

- [ ] **Step 1: 编写失败测试（系统路由）**

对 `GET /api/system/health` 返回 200 与 JSON（如 `{"status":"ok"}`）；对 `POST /api/system/shutdown` 在测试中可 mock `server.should_exit` 或回调，断言被调用。使用 `TestClient`。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_system_routes.py -v`
预期：FAIL。

- [ ] **Step 3: 实现 FastAPI 应用与系统路由**

创建 `gateway/routes/system.py` 注册 `/api/system/health` 与 `/api/system/shutdown`；在 `main.py` 中构建 `FastAPI()`，挂载 system 路由；固定采用白皮书方案 A：使用 `uvicorn.Server(config)` 的程序化启动方式，将 Task 4 中已绑定的 socket 传给 Uvicorn；在 FastAPI lifespan startup 中于应用、插件、鉴权与 ProcessManager 全部初始化完成后原子写入 ready_file；仅当 ready payload 为 `status="ready"` 时宿主才继续初始化。若启动失败，删除旧 ready_file 或写入 `status="error"` 供宿主报错。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_system_routes.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): FastAPI app with system routes and programmatic Uvicorn"
```

---

### Task 6: 宿主存活监控（`host_pid`）

**Files:**
- Create: `gateway/gateway/host_liveness.py`
- Modify: `gateway/gateway/main.py`
- Test: `gateway/tests/test_host_liveness.py`

- [ ] **Step 1: 编写失败测试**

在 `gateway/tests/test_host_liveness.py` 中：给定当前进程 PID 时，宿主存活检查返回存活；给定不存在的 PID 时，存活检查返回死亡；给定一个可注入的 `on_host_exit` 回调时，轮询协程在检测到宿主死亡后触发回调，回调中可设置 `server.should_exit = True` 并终止受托管子进程。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_host_liveness.py -v`
预期：FAIL。

- [ ] **Step 3: 实现宿主存活监控**

在 `host_liveness.py` 中实现跨平台宿主存活检查与轮询协程：1) `is_host_alive(host_pid)`；2) `start_host_liveness_watch(host_pid, on_host_exit, poll_interval)`。在 `main.py` 中将其接入应用生命周期；检测到宿主死亡时执行统一收束：`ProcessManager.terminate_all()`、删除 ready_file、设置 `server.should_exit = True`。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_host_liveness.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): add host liveness monitoring for host_pid shutdown"
```

---

### Task 7: 鉴权中间件与 CORS

**Files:**
- Create: `gateway/gateway/auth.py`
- Test: `gateway/tests/test_auth.py`

- [ ] **Step 1: 编写失败测试**

请求无 `Authorization: Bearer <token>` 时，`GET /api/system/health` 返回 401；带正确 token 时返回 200；CORS 不允许 `*`，仅允许配置的 `allowed_origin`；若 Origin 不匹配则预检失败或不返回允许头。`/api/system/health` 不再视为公开路径。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_auth.py -v`
预期：FAIL。

- [ ] **Step 3: 实现鉴权与 CORS**

在 `auth.py` 中实现依赖项或中间件：从 Header 读取 `Authorization: Bearer <token>`，与 config 中 `auth_token` 比对；HTTP 路由默认要求鉴权；CORS 使用 `CORSMiddleware`，`allow_origins=[config.allowed_origin]`，禁止 `["*"]`。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_auth.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): Bearer auth middleware and constrained CORS"
```

---

### Task 8: ProcessManager 与优雅停机

**Files:**
- Create: `gateway/gateway/process_manager.py`
- Test: `gateway/tests/test_process_manager.py`

- [ ] **Step 1: 编写失败测试**

启动一个跨平台长活子进程，优先使用 `sys.executable -c "import time; time.sleep(60)"`；通过 ProcessManager 注册；调用 `terminate_all()` 后断言子进程已退出（轮询或 timeout）。若子进程再派生受同组约束的子进程，Unix 下验证进程组被清理；Windows 至少验证主子进程可被统一结束。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_process_manager.py -v`
预期：FAIL。

- [ ] **Step 3: 实现 ProcessManager**

`ProcessManager` 维护子进程列表；`spawn(args)` 使用 `subprocess.Popen`，并做进程组/`setsid` 或 Windows Job/creation flags 绑定；`terminate_all()` 先发送温和终止，再等待，必要时强制 kill；禁止插件绕过 `ProcessManager` 启动受托管进程。在 `POST /api/system/shutdown` 与宿主猝死回调中都复用同一收尾逻辑。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_process_manager.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): ProcessManager for subprocess lifecycle and shutdown"
```

---

### Task 9: 资源解析器（禁止全局 chdir）

**Files:**
- Create: `gateway/gateway/resource_resolver.py`
- Test: `gateway/tests/test_resource_resolver.py`

- [ ] **Step 1: 编写失败测试**

`get_resource_path("foo/bar.txt")` 在开发环境下返回基于项目根或包位置的路径；在 PyInstaller 下可 mock `sys._MEIPASS` 断言返回 `os.path.join(sys._MEIPASS, "foo/bar.txt")`；在通用 frozen 环境下可 mock `sys.frozen` 与 `sys.executable` 断言路径基于可执行目录解析。不依赖全局 `os.getcwd()` 为 data_dir。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_resource_resolver.py -v`
预期：FAIL。

- [ ] **Step 3: 实现 get_resource_path**

若存在 `sys._MEIPASS` 则基于其拼接；若为其他 frozen 环境则基于 `Path(sys.executable).resolve().parent` 或等价资源根拼接；否则基于 `__file__` 或包根目录计算资源根目录再拼接 relative_path。不在主进程内调用 `os.chdir(data_dir)`。

- [ ] **Step 4: 运行测试通过**

`python -m pytest gateway/tests/test_resource_resolver.py -v`
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add gateway/
git commit -m "feat(gateway): resource resolver for dev and frozen env, no global chdir"
```

---

## Phase 3：API 插件与宿主侧集成

### Task 10: 插件加载器（Manifest + setup(context)）

**Files:**
- Create: `gateway/gateway/plugin_loader.py`
- Test: `gateway/tests/test_plugin_loader.py`
- Create: `plugins/example_api/manifest.json`
- Create: `plugins/example_api/entry.py`

- [ ] **Step 1: 编写失败测试**

给定插件目录包含 `manifest.json`（含 `type: "api"`, `entry: "entry:setup"`）和 `entry.py` 定义 `setup(context)` 并往 `context.app` 挂载一个路由；加载后请求该路由返回预期 JSON。

- [ ] **Step 2: 运行测试确认失败**

`python -m pytest gateway/tests/test_plugin_loader.py -v`
预期：FAIL。

- [ ] **Step 3: 实现插件加载器**

`plugin_loader.py`：扫描指定 plugins 目录，读取每个子目录的 `manifest.json`，根据 `entry` 动态加载并调用 `setup(context)`。`context` 至少包含 `app`, `data_dir`, `auth`, `process_manager`, `resource_resolver`（可先传最小集）。在 `main.py` 中在创建 app 后、启动 server 前调用加载器。

- [ ] **Step 4: 实现 example_api 插件**

`plugins/example_api/manifest.json`: `{"type":"api","entry":"entry:setup","name":"example_api"}`。`entry.py`: `def setup(context): context.app.include_router(APIRouter(prefix="/api/example"), ...)`，注册一个 GET 返回 `{"plugin":"example_api"}`。

- [ ] **Step 5: 运行测试通过**

`python -m pytest gateway/tests/test_plugin_loader.py -v`
预期：PASS。

- [ ] **Step 6: Commit**

```bash
git add gateway/ plugins/
git commit -m "feat(gateway): plugin loader with manifest and example API plugin"
```

---

### Task 11: Tauri 启动网关、轮询 ready_file、暴露端口与鉴权给前端

**Files:**
- Create: `src-tauri/src/gateway.rs`
- Modify: `src-tauri/src/lib.rs`
- Modify: `src-tauri/tauri.conf.json`（若需注入 Origin）

- [ ] **Step 1: 实现 gateway 模块**

在 `gateway.rs` 中：接收参数 `data_dir`, `auth_token`, `ready_file`, `host_pid`, `allowed_origin`；启动前删除旧 ready_file；开发时固定以 `python -m gateway.main` 启动，工作目录设为 `gateway/`；发布时启动打包后的网关可执行文件；使用 `std::process::Command` 启动子进程，传入 `--data-dir`, `--auth-token`, `--ready-file`, `--host-pid`, `--allowed-origin`。轮询 ready_file 时只接受 `status=="ready"`、`pid` 与当前子进程 PID 一致且 JSON 可解析的结果；若超时（如 30s）或读到 `status=="error"` 则报错退出。提供函数返回 `(port, auth_token)`。

- [ ] **Step 2: 宿主启动时调用并暴露给前端**

在 Tauri 的 `setup` 或应用启动流程中调用 gateway 启动与轮询；将 `base_url`（如 `http://127.0.0.1:{port}`）和 `auth_token` 通过 Tauri 的 `manage` 或 `invoke` 暴露给前端，或写入前端可读的全局/环境（如 `window.__GATEWAY__`）。开发态与生产态分别注入真实 WebView Origin，统一通过 `--allowed-origin` 传给网关。

- [ ] **Step 3: 验证 E2E**

运行 Tauri 应用，确认窗口打开后前端能拿到 base_url 和 token；前端用 fetch 带 `Authorization: Bearer <token>` 请求 `GET /api/system/health` 返回 200。

- [ ] **Step 4: Commit**

```bash
git add src-tauri/
git commit -m "feat(tauri): spawn gateway, poll ready_file, expose port and auth to frontend"
```

---

### Task 12: 优雅停机（关闭窗口 → shutdown API → 网关退出）

**Files:**
- Modify: `src-tauri/src/lib.rs`（或 main）
- Modify: `gateway/gateway/routes/system.py`

- [ ] **Step 1: Rust 拦截窗口关闭**

在 Tauri 中监听窗口关闭事件，阻止直接退出；先发 `POST {base_url}/api/system/shutdown`（带 Bearer token），等待短时间（如 2s）再允许窗口关闭并退出进程。若 shutdown API 超时或失败，则记录错误并对网关子进程执行兜底终止，避免窗口已关闭但 sidecar 残留。

- [ ] **Step 2: 网关 shutdown 收尾**

确认 `POST /api/system/shutdown` 内已设置 `server.should_exit = True` 并调用 `ProcessManager.terminate_all()`；Uvicorn 使用 lifespan 或 shutdown 钩子做收尾。

- [ ] **Step 3: 验证**

启动 Tauri，关闭窗口，确认 Python 进程退出且无僵尸子进程。

- [ ] **Step 4: Commit**

```bash
git add src-tauri/ gateway/
git commit -m "feat: graceful shutdown on window close via /api/system/shutdown"
```

---

## Phase 4：前端 SDK 与基础 UI

### Task 13: 前端 API 客户端与健康检查 UI

**Files:**
- Create: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 实现 SDK 客户端**

从 Tauri 注入的 `window.__GATEWAY__`（或等价）读取 `baseUrl` 与 `token`；封装 `get(path)`, `post(path, body)`，请求时自动加上 `Authorization: Bearer ${token}` 和 `baseUrl`。

- [ ] **Step 2: 健康检查 UI**

在 `App.tsx` 中调用 `GET /api/system/health`，显示 "Gateway: ok" 或错误信息；可选调用 example 插件 `GET /api/example` 显示插件名。

- [ ] **Step 3: 验证**

在 Tauri 中打开应用，确认页面显示网关与插件状态。

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): API client and health/plugin status UI"
```

---

## Phase 5：构建与打包（最小可行）

### Task 14: Python 网关可执行与 Tauri 集成

**Files:**
- Create: `gateway/scripts/scan_plugins.py`
- Create: `gateway/scripts/build_gateway.sh` 或 PyInstaller spec
- Modify: `src-tauri/src/gateway.rs`（打包时指向网关可执行路径）

- [ ] **Step 1: 预构建扫描脚本**

实现 `gateway/scripts/scan_plugins.py`：扫描 `plugins/` 下的 `manifest.json` 与入口模块，输出显式 import / hidden-import 列表以及需要打包的数据目录；MVP 允许扫描规则先覆盖 API 插件，但不允许完全写死插件列表跳过扫描步骤。

- [ ] **Step 2: 打包脚本**

使用 PyInstaller 将 `gateway.main` 打成单目录或单文件；打包前先调用扫描脚本生成参数；包含 `gateway` 包与 `plugins` 目录；输出到 `dist/gateway` 或 Tauri 资源目录。MVP 明确只交付 PyInstaller 轨道；`Nuitka` 不在本任务实现，待 PyInstaller 链路稳定后进入 Phase 2。

- [ ] **Step 3: Tauri 侧使用打包后的网关**

在 `gateway.rs` 中，开发时使用 `python -m gateway.main`；发布时直接执行打包后的网关可执行文件，不得把冻结产物当作“python 解释器”再次执行脚本；通过 `tauri.conf.json` 的 resources 或环境变量配置定位网关产物。

- [ ] **Step 4: 验证**

执行 Tauri 的 production 构建，安装并运行，确认网关从打包产物启动、ready_file 与鉴权正常；额外验证冻结环境下不会递归自启、不会把自身当解释器二次启动，插件代码与静态资源均已随包可用。

- [ ] **Step 5: Commit**

```bash
git add gateway/scripts/ src-tauri/
git commit -m "chore: package Python gateway and integrate with Tauri build"
```

---

## 验收标准（MVP）

- Tauri 应用启动后自动启动 Python 网关，通过带 `status="ready"` 的 ready_file 获取端口，无日志解析；宿主启动前会清理旧 ready_file。
- 前端通过 Bearer token 调用 `/api/system/health` 与示例 API 插件接口，CORS 非 `*`。
- 宿主正常关闭时触发 `POST /api/system/shutdown`，网关与子进程优雅退出；宿主异常退出时，Python 网关能通过 `host_pid` 轮询自行收束退出。
- 数据目录与资源路径通过配置与 context 注入，无全局 `os.chdir(data_dir)`。
- Tauri 到网关的 Origin 配置链路完整，`allowed_origin` 由宿主注入，计划中无写死 `*` 或未定义 Origin 的实现空洞。
- 至少一个 API 插件通过 manifest + `setup(context)` 挂载并可被前端调用。
- 可完成一次从源码到 Tauri 安装包（或 dev run）的端到端运行，且 PyInstaller 打包前会先运行预构建扫描脚本。

---

## 不包含在 MVP（留待 Phase 2/3）

- 服务型插件、MCP 插件、OpenAPI 聚合、SSE、WebSocket 代理、插件市场与启停管理界面。
- Nuitka 打包轨道明确留待 Phase 2，在 PyInstaller 轨道、插件扫描与冻结态集成稳定后再实现；多类型插件复杂打包适配可继续留待 Phase 2/3。MVP 只要求 PyInstaller 轨道跑通，但扫描器仍为必做基建。

---

## 计划审查与执行

- 若存在 plan-document-reviewer 子 agent，对本计划做一次审查后再进入执行。
- 执行时使用 @superpowers:subagent-driven-development 或 @superpowers:executing-plans，按任务与步骤勾选推进，每步提交保持历史可追溯。
