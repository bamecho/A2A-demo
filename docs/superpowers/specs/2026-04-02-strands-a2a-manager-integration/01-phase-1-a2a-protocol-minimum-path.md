# Phase 1 Spec: A2A 协议最小通路

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 在当前仓库中建立一个可运行的最小 FastAPI + Strands A2A server 样例，让标准 A2A SDK 请求可以收到文本流式响应。

**Architecture:** 使用单个 FastAPI 宿主承载 A2A 路由。先接一个最小 stub agent 或等价 fake stream producer，不引入 manager 复用逻辑，只验证协议入站、宿主挂载与文本 streaming。

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, strands-agents SDK, pytest, httpx

---

## Scope

In scope:

- Python 应用骨架
- FastAPI app factory
- A2A server 挂载
- 最小文本流式响应
- 一个端到端集成测试

Out of scope:

- 真实 manager
- HTTP 身份注入
- 复杂输入映射
- 错误契约细化

## File plan

- Create: `pyproject.toml`
- Create: `src/strands_a2a_bridge/__init__.py`
- Create: `src/strands_a2a_bridge/app.py`
- Create: `src/strands_a2a_bridge/config.py`
- Create: `src/strands_a2a_bridge/a2a/__init__.py`
- Create: `src/strands_a2a_bridge/a2a/server.py`
- Create: `src/strands_a2a_bridge/a2a/stub_agent.py`
- Create: `tests/integration/test_phase1_a2a_streaming.py`
- Create: `tests/conftest.py`

## Execution tasks

### Task 1: Python runtime skeleton

- [ ] 创建 `pyproject.toml`，声明最小依赖：`fastapi`、`uvicorn`、`pytest`、`httpx`、`strands-agents`
- [ ] 创建 `src/strands_a2a_bridge/__init__.py` 和 `src/strands_a2a_bridge/a2a/__init__.py`
- [ ] 在 `src/strands_a2a_bridge/config.py` 定义最小配置对象：host、port、public_url、service_name

Verification:

- Run: `python -m pytest --version`
- Expected: pytest 可执行

### Task 2: 宿主 FastAPI app factory

- [ ] 在 `src/strands_a2a_bridge/app.py` 创建 `create_app()`，只负责初始化 FastAPI 与挂载 A2A 路由
- [ ] 在 `src/strands_a2a_bridge/a2a/server.py` 创建 `build_a2a_router()` 或等价封装，保持协议层独立于 app factory

Implementation notes:

- `app.py` 不直接理解 stub agent 细节，只通过 `a2a/server.py` 获取可挂载对象
- 路由前缀固定为 `/a2a`

Verification:

- Run: `python -c "from strands_a2a_bridge.app import create_app; app = create_app(); print(app.title)"`
- Expected: 成功输出应用标题，无导入错误

### Task 3: 最小 stub agent streaming

- [ ] 在 `src/strands_a2a_bridge/a2a/stub_agent.py` 提供一个最小流生产器，行为固定且可预测
- [ ] 在 `src/strands_a2a_bridge/a2a/server.py` 将该流生产器接入 A2A 执行链

Implementation notes:

- 只支持文本输入和文本输出
- 流式内容保持固定，例如 `hello`, `from`, `stub-agent`
- 不要在 Phase 1 引入 manager 抽象

Verification:

- Run: `python -m pytest tests/integration/test_phase1_a2a_streaming.py -v`
- Expected: 能收到多个增量文本事件，测试通过

### Task 4: 端到端集成测试

- [ ] 在 `tests/conftest.py` 提供测试 app fixture
- [ ] 在 `tests/integration/test_phase1_a2a_streaming.py` 编写一个端到端测试，验证标准请求进入后能拿到流式文本输出

Test assertions:

- 响应由多个文本 chunk 组成，而不是一次性静态字符串
- A2A endpoint 运行在 FastAPI app 内
- 未引入 manager 也能完成最小闭环

### Task 5: 运行与文档校验

- [ ] 记录本 phase 的启动命令和最小验证命令
- [ ] 确认 Phase 1 代码不泄漏对 Phase 2+ 的隐式依赖

Verification:

- Run: `python -m pytest tests/integration/test_phase1_a2a_streaming.py -v`
- Expected: PASS

## Done definition

- 可以在当前仓库启动一个最小 A2A 服务
- 集成测试证明流式文本响应成立
- 没有引入 manager、身份上下文或并发治理的额外复杂度

## Status

- [x] Completed

## Review

- Outcome: FastAPI 宿主已挂载真实 A2A 子应用到 `/a2a`，标准 A2A streaming 请求可返回稳定文本增量。
- Verification:
  `uv run python -m pytest tests/integration/test_phase1_a2a_streaming.py -v`
  `uv run python -m pytest -v`
- Notes: 非文本输入现在会被明确拒绝，错误为 `-32602` / `Only text input parts are supported in Phase 1`；Python 版本约束已对齐为 `>=3.11`。
