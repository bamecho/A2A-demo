# Phase 3 Spec: Manager 适配契约与模拟实现

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 定义 A2A 层与内部 manager 之间的稳定适配契约，并在当前仓库中用 fake manager/fake agent 模拟按 `user_id` 创建或复用 agent 的行为。

**Architecture:** 引入单独的 manager adapter 层，A2A executor 只依赖抽象接口，不依赖真实内部 manager。当前仓库提供 fake manager 实现，用于证明复用语义、隔离边界和未来替换路径。

**Tech Stack:** Python 3.11+, FastAPI, dataclasses or pydantic, pytest

---

## Scope

In scope:

- manager adapter 契约
- fake manager
- fake agent
- `get_or_create_agent(user_id)` 行为
- 同用户复用与不同用户隔离测试

Out of scope:

- 真实内部 manager 接入
- 工具调用透传
- 复杂记忆持久化

## File plan

- Create: `src/strands_a2a_bridge/manager/__init__.py`
- Create: `src/strands_a2a_bridge/manager/contracts.py`
- Create: `src/strands_a2a_bridge/manager/fake.py`
- Modify: `src/strands_a2a_bridge/a2a/server.py`
- Create: `tests/unit/test_fake_manager.py`
- Create: `tests/integration/test_phase3_manager_adapter.py`

## Execution tasks

### Task 1: 定义 manager adapter 契约

- [ ] 在 `src/strands_a2a_bridge/manager/contracts.py` 定义 `AgentProvider` 或等价协议
- [ ] 该契约只暴露最少接口：根据 `user_id` 获取 agent、报告 agent 标识、可选暴露执行能力
- [ ] 文档化“不在 A2A 层管理 agent 生命周期”的边界

Implementation notes:

- 契约必须足够薄，避免提前编码真实 manager 的内部细节
- 未来内部接入只应该替换 adapter 实现，而不是改 A2A server

### Task 2: fake manager/fake agent 实现

- [ ] 在 `src/strands_a2a_bridge/manager/fake.py` 实现 fake manager
- [ ] fake manager 以 `user_id` 为键缓存 fake agent
- [ ] fake agent 暴露最小 stream 接口，并保留一个可观测身份标识，用于测试复用

Verification:

- Run: `python -m pytest tests/unit/test_fake_manager.py -v`
- Expected: 同一 `user_id` 返回同一 fake agent，不同用户返回不同 fake agent

### Task 3: executor 改为依赖 adapter

- [ ] 修改 `src/strands_a2a_bridge/a2a/server.py`
- [ ] 将 Phase 1 的直接 stub stream 改为“从 adapter 取 agent，再消费该 agent 的 stream”
- [ ] 保证 A2A 层只与契约交互，不直接理解 fake manager 的内部存储

### Task 4: 集成测试复用语义

- [ ] 在 `tests/integration/test_phase3_manager_adapter.py` 覆盖同一用户两次请求的 agent 复用
- [ ] 在 `tests/integration/test_phase3_manager_adapter.py` 覆盖不同用户隔离
- [ ] 在测试断言中使用 fake agent identity 或 sequence id 证明复用发生

## Done definition

- A2A 层已通过独立 adapter 契约获取 agent
- 当前仓库存在可运行的 fake manager/fake agent 模拟实现
- 复用与隔离语义已通过自动化测试证明
