# Confluox v0.2.4：案例模板与运行时冒烟测试

发布日期：2026-03-19
标签：`v0.2.4-case-study-templates-and-smoke-tests`

## 亮点

- 在 `plugins/examples/` 新增可复制的案例插件模板。
- 新增运行时冒烟测试，确保案例模板可实际启动与调用。
- 在 CI 中加入文档/模板一致性与运行时守护。

## 本次落地内容

### 1. 案例模板

- `plugins/examples/whisper_oop_template`
- `plugins/examples/index_worker_template`
- `plugins/examples/md_builder_template`

### 2. 运行时冒烟覆盖

- 新增 `gateway/tests/test_case_study_templates_runtime.py`
- 覆盖：
  - in-process 模板路由回路（`/api/md/build`）
  - out-of-process 模板代理回路（`/api/whisper_app/transcribe`）

### 3. CI 守护

- `ci-dual-track` 新增执行：
  - `gateway/tests/test_case_study_assets.py`
  - `gateway/tests/test_case_study_templates_runtime.py`

## 验证快照

- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_assets.py -q` -> 通过
- `PYTHONPATH=$PWD/gateway python3 -m pytest gateway/tests/test_case_study_templates_runtime.py -q` -> 通过
- `cd gateway && python3 -m pytest tests -q` -> 通过
