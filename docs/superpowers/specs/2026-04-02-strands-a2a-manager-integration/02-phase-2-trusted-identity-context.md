# Phase 2 Spec: 可信身份上下文接入

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 在 A2A 请求链路前建立可信身份上下文注入机制，让执行链只能消费 HTTP 层认证后的 `user_id` 与 `request_id`。

**Architecture:** 在 FastAPI 中间件或依赖层解析受信任请求头，生成统一 `RequestContext`，再通过上下文桥接机制让 A2A 执行链读取。A2A payload 不再承担身份来源职责。

**Tech Stack:** Python 3.11+, FastAPI, contextvars, pytest, httpx

---

## Scope

In scope:

- `RequestContext` 模型
- HTTP 层可信头解析
- `request_id` 注入
- A2A 执行链读取上下文
- 认证失败与上下文缺失测试

Out of scope:

- 真实 JWT 校验
- 外部网关集成
- manager 复用逻辑

## File plan

- Modify: `src/strands_a2a_bridge/app.py`
- Create: `src/strands_a2a_bridge/http/__init__.py`
- Create: `src/strands_a2a_bridge/http/context.py`
- Create: `src/strands_a2a_bridge/http/auth.py`
- Modify: `src/strands_a2a_bridge/a2a/server.py`
- Create: `tests/integration/test_phase2_identity_context.py`
- Create: `tests/unit/test_request_context.py`

## Execution tasks

### Task 1: 定义统一请求上下文

- [ ] 在 `src/strands_a2a_bridge/http/context.py` 定义 `RequestContext`
- [ ] 字段至少包含：`user_id`、`request_id`、`trace_id`
- [ ] 提供 `set_current_request_context()`、`get_current_request_context()` 或等价 API

Verification:

- Run: `python -m pytest tests/unit/test_request_context.py -v`
- Expected: 上下文设置与读取行为通过

### Task 2: HTTP 层可信头解析

- [ ] 在 `src/strands_a2a_bridge/http/auth.py` 定义最小身份解析器
- [ ] 只信任明确约定的请求头，例如 `x-user-id`、`x-request-id`
- [ ] 缺少 `x-user-id` 时直接返回认证错误，不进入 A2A 执行链

Implementation notes:

- Phase 2 只模拟受信任内部调用，不引入完整 JWT 依赖
- 如果未提供 `x-request-id`，服务端生成一个稳定可记录的值

### Task 3: 将上下文桥接到 A2A 执行链

- [ ] 修改 `src/strands_a2a_bridge/app.py`，在请求入口设置上下文
- [ ] 修改 `src/strands_a2a_bridge/a2a/server.py`，让执行逻辑从上下文桥接层读取 `RequestContext`
- [ ] 明确禁止从 A2A payload metadata 读取 `user_id`

Verification:

- Run: `python -m pytest tests/integration/test_phase2_identity_context.py -v`
- Expected: 请求头中的 `x-user-id` 能被执行链观察到

### Task 4: 失败路径测试

- [ ] 在 `tests/integration/test_phase2_identity_context.py` 覆盖缺失 `x-user-id`
- [ ] 在 `tests/integration/test_phase2_identity_context.py` 覆盖请求体伪造 `user_id` 但请求头为空的场景
- [ ] 在 `tests/unit/test_request_context.py` 覆盖上下文清理行为

Test assertions:

- 缺失可信头时直接失败
- payload 中伪造身份不会被信任
- 每个请求结束后上下文会被清理

## Done definition

- HTTP 层是唯一可信身份来源
- A2A 执行链稳定读取 `RequestContext`
- 认证失败与上下文缺失行为已自动化验证

## Status

- [x] Completed

## Review

- Outcome: 可信身份上下文只来自 HTTP 头，并通过 `ServerCallContext.state` 桥接进 A2A 执行链；payload 身份伪造被忽略。
- Verification:
  `uv run python -m pytest tests/unit/test_request_context.py -v`
  `uv run python -m pytest tests/integration/test_phase2_identity_context.py -v`
  `uv run python -m pytest -v`
- Notes: 缺失 `x-user-id` 时在进入 A2A 前直接返回 `401`；请求结束后上下文会清理。
