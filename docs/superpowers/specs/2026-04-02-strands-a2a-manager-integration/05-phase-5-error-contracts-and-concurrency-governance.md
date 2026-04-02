# Phase 5 Spec: 错误契约与并发治理

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 让失败路径和并发路径都具备确定性行为，避免在同用户并发、上下文缺失或执行异常时暴露内部细节或触发不可控竞态。

**Architecture:** 引入独立错误映射层和用户级并发控制模块。执行链在获取 agent 前先应用并发策略，在输出阶段统一捕获并映射异常，对外暴露稳定错误契约。

**Tech Stack:** Python 3.11+, asyncio, pytest, FastAPI

---

## Scope

In scope:

- 用户级并发控制
- 统一错误模型
- 同用户 busy/串行策略
- 不同用户并行行为
- 客户端断连时的最佳努力清理

Out of scope:

- 真正的远程取消
- 任务持久化
- 多租户复杂配额

## File plan

- Create: `src/strands_a2a_bridge/concurrency/__init__.py`
- Create: `src/strands_a2a_bridge/concurrency/user_lock.py`
- Create: `src/strands_a2a_bridge/errors.py`
- Modify: `src/strands_a2a_bridge/a2a/server.py`
- Modify: `src/strands_a2a_bridge/http/auth.py`
- Create: `tests/unit/test_user_lock.py`
- Create: `tests/unit/test_error_mapping.py`
- Create: `tests/integration/test_phase5_error_and_concurrency.py`

## Execution tasks

### Task 1: 用户级并发控制模块

- [ ] 在 `src/strands_a2a_bridge/concurrency/user_lock.py` 定义按 `user_id` 控制的并发守卫
- [ ] 策略固定为：同一用户已有活跃请求时返回 busy，第一版不做内存队列
- [ ] 不同用户请求互不阻塞

Verification:

- Run: `python -m pytest tests/unit/test_user_lock.py -v`
- Expected: 同用户二次进入被拒绝，不同用户可以同时进入

### Task 2: 统一错误映射

- [ ] 在 `src/strands_a2a_bridge/errors.py` 定义领域错误类型与公开错误码
- [ ] 修改 `src/strands_a2a_bridge/http/auth.py` 和 `src/strands_a2a_bridge/a2a/server.py`，统一走错误映射出口
- [ ] 对外只暴露稳定错误信息和 `request_id`，不暴露 traceback

Verification:

- Run: `python -m pytest tests/unit/test_error_mapping.py -v`
- Expected: 认证失败、busy、agent error 都能映射到稳定错误响应

### Task 3: 失败路径与并发集成测试

- [ ] 在 `tests/integration/test_phase5_error_and_concurrency.py` 覆盖缺失 `x-user-id`
- [ ] 覆盖同一用户并发请求 busy
- [ ] 覆盖不同用户并行请求都成功
- [ ] 覆盖 fake agent 主动抛错时的统一错误响应

## Done definition

- 同用户并发策略已变成外部可观察行为
- 主要错误路径都有稳定契约
- 不同用户并行场景不会发生上下文污染
