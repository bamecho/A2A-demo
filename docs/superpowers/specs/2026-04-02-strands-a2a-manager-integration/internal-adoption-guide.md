# Internal Adoption Guide

> Audience: 把当前仓库中的 A2A bridge 迁入真实内部 Strands manager 代码库的接入者

## Goal

当前仓库已经验证了以下第一版行为可以成立：

- FastAPI 宿主内挂载标准 A2A server
- 可信 `user_id` / `request_id` / `trace_id` 只从 HTTP 头进入
- A2A 层按请求动态获取用户 agent，而不是绑定单一 agent
- 同用户并发请求返回 busy，不做内存队列
- manager 异常、agent 异常和认证失败都映射为稳定错误契约

迁入真实内部系统时，目标不是重写整个 bridge，而是替换模拟 manager，并保留已经验证过的协议层、上下文层、mapper 和错误/并发治理。

## Modules To Reuse As-Is

以下模块可以直接迁移到内部仓库，或作为迁移时的基准实现：

- `src/strands_a2a_bridge/app.py`
- `src/strands_a2a_bridge/a2a/server.py`
- `src/strands_a2a_bridge/http/auth.py`
- `src/strands_a2a_bridge/http/context.py`
- `src/strands_a2a_bridge/a2a/mapping.py`
- `src/strands_a2a_bridge/concurrency/user_lock.py`
- `src/strands_a2a_bridge/errors.py`
- `src/strands_a2a_bridge/manager/contracts.py`

这些文件定义了第一版稳定边界：

- HTTP 身份边界
- A2A 请求到内部 agent 输入的映射
- 同用户并发 busy 策略
- 公共错误契约
- manager 接口缝隙

## Modules That Must Be Replaced

唯一必须替换的模拟部分是 fake manager/fake agent：

- `src/strands_a2a_bridge/manager/fake.py`

在真实内部系统中，应由真实 manager adapter 替代默认 `FakeAgentProvider()` 的注入位置。

## Required Interface Alignment

### 1. `user_id`

- 真实 manager 必须继续把 `user_id` 视为可信上游上下文，而不是从 A2A payload metadata 中读取
- `user_id` 的唯一来源仍应是 HTTP 鉴权链路或受信任网关

### 2. Agent 获取

- A2A 层只依赖 `AgentProvider.get_or_create_agent(user_id)`
- 真实实现应保证同一用户命中同一会话/agent 复用语义，不要求 A2A 层理解 manager 内部缓存或保活逻辑

### 3. Stream 接口

- 返回的 agent 必须满足 `ManagedAgent.stream_async(content_blocks, invocation_state=None)`
- 第一版只要求文本输入和文本流式输出
- 如果真实 agent 输出更复杂事件，应先在内部收敛成 bridge 可消费的文本增量/终态，再决定是否扩展协议层

### 4. Error Boundary

- manager 获取失败应允许向外冒泡，由 `errors.py` 统一映射为稳定公共错误
- agent 执行异常不应把 traceback 或内部类名透传给客户端
- 对外应继续保留 `request_id`，用于跨网关、A2A bridge 和内部 manager 追踪

## Minimal Replacement Steps

1. 在内部仓库实现一个新的 `AgentProvider`，用真实 manager 替代 `FakeAgentProvider`
2. 保留 `create_app(..., provider=real_provider)` 或等价注入方式，不要把真实 manager 逻辑直接写进 A2A handler
3. 保留 `UserRequestGuard` 或提供等价策略，确保同用户并发仍表现为 busy
4. 保留 `errors.py` 的统一映射出口，避免真实 manager 的内部异常形态泄漏到外部
5. 完成后按 [`validation-checklist.md`](./validation-checklist.md) 逐项回归

## First-Version Boundaries

第一版明确支持：

- 文本输入
- 文本流式输出
- 同用户复用
- 同用户 busy
- 不同用户并行
- 统一错误契约

第一版明确不支持：

- 持久任务状态
- 断线恢复 / 重连续传
- 远程取消
- 多模态 parts / 文件输入
- 完整工具事件透传

## Recommended Internal Rollout

- 先在内部仓库以 fake provider 对照真实 provider 做双实现装配
- 保留本仓库的 phase1-5 行为作为最小验收面
- 只有当协议、身份、复用、busy、并行和错误路径全部过线后，再考虑扩展更完整的 task lifecycle
