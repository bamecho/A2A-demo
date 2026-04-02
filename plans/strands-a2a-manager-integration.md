# Plan: Strands A2A Server 与 Agent Manager 集成

> Source PRD: `docs/prd/2026-04-02-strands-a2a-manager-integration-prd.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Ingress**: 在现有 FastAPI 宿主中挂载标准 A2A server，不单独起第二套服务。
- **Identity boundary**: 可信 `user_id`、`request_id` 和 trace 上下文只从 HTTP 鉴权链路或受信任网关注入中获取，不信任 A2A 请求体自报身份。
- **Execution ownership**: agent 生命周期、上下文复用和保活策略由内部 `manager` 负责；A2A 层只做协议接入、输入映射、输出映射和错误映射。
- **Integration seam**: 通过自定义的 manager-backed executor/adapter 在每次请求时动态获取 agent，而不是使用固定绑定单个 agent 的默认执行模型。
- **Capability scope**: 第一版仅支持文本输入与文本流式输出；不包含持久任务状态、断线恢复、远程取消、多模态和完整工具事件透传。
- **Concurrency policy**: 同一 `user_id` 的并发请求采用串行化或明确返回 busy；不同 `user_id` 的请求允许并行。
- **Delivery constraint**: 当前仓库无法直接接入真实内部代码，因此实施采用“契约层 + fake manager/fake agent 模拟实现”的方式验证方案，并提供迁入内部系统的替换说明。
- **Verification strategy**: 测试以端到端协议与流式集成验证为主，补充关键 mapper/translator/provider 的单元测试。

---

## Phase 1: A2A 协议最小通路

**User stories**: 1, 2, 8, 14, 15, 21

### What to build

建立一个可运行的最小 A2A 服务切片：在 FastAPI 宿主中挂出标准 A2A 入口，接收标准 A2A SDK 请求，并通过一个最小 stub agent 返回文本流。该阶段不引入真实 manager，也不追求能力面对齐，目标是先证明标准协议、宿主挂载方式和流式响应链路成立。

### Acceptance criteria

- [x] 可以通过标准 A2A SDK 向服务端发起请求并收到文本流式响应
- [x] A2A server 运行在现有 FastAPI 宿主内，而不是独立服务
- [x] 最小实现有自动化验证，证明基础协议通路和 streaming 行为成立

### Review

- Outcome: 已完成。FastAPI 宿主挂载真实 A2A 子应用到 `/a2a`，支持标准 A2A streaming 请求，文本输出为稳定 chunk。
- Verification: `uv run python -m pytest tests/integration/test_phase1_a2a_streaming.py -v` 通过；`uv run python -m pytest -v` 通过。
- Notes: 已补充非文本输入拒绝，错误为 `-32602` / `Only text input parts are supported in Phase 1`；`requires-python` 已对齐为 `>=3.11`。

---

## Phase 2: 可信身份上下文接入

**User stories**: 4, 5, 9, 19, 21

### What to build

在 A2A 请求链路前增加 HTTP 身份上下文解析层，将可信 `user_id`、`request_id` 和 trace 信息注入执行上下文，并让 A2A 执行链可以消费这些字段。该阶段仍可使用 stub manager，但必须把身份边界与协议负载彻底分开。

### Acceptance criteria

- [x] 系统只从 HTTP 层可信来源解析 `user_id`，不依赖 A2A payload 自报身份
- [x] 每次 A2A 请求都能在执行链中获得统一的请求上下文
- [x] 认证失败、缺失身份上下文等场景有清晰且稳定的错误行为

### Review

- Outcome: 已完成。可信身份上下文只来自 HTTP 头，并通过 `call_context.state` 桥接进 A2A 执行链。
- Verification: `uv run python -m pytest tests/unit/test_request_context.py -v` 通过；`uv run python -m pytest tests/integration/test_phase2_identity_context.py -v` 通过；`uv run python -m pytest -v` 通过。
- Notes: 缺失 `x-user-id` 时在进入 A2A 前返回 `401`；payload 中伪造的 `user_id` / `request_id` / `trace_id` 不被信任；请求结束后上下文会清理。

---

## Phase 3: Manager 适配契约与模拟实现

**User stories**: 6, 7, 10, 23, 24

### What to build

定义 manager-backed adapter 的稳定契约，并在当前仓库提供 fake manager/fake agent 的模拟实现，用于模拟“按 `user_id` 创建或复用 agent”的行为。该切片的目标不是复制真实内部逻辑，而是把未来替换真实 manager 所需的接口边界固定下来，并证明 A2A 层不会直接拥有 agent 生命周期。

### Acceptance criteria

- [x] 存在清晰、独立的 manager adapter 契约，A2A 层仅通过该契约获取 agent
- [x] fake manager 能模拟同用户复用与不同用户隔离的核心行为
- [x] 替换 fake manager 为真实内部 manager 时，主要改动集中在 adapter 层

### Review

- Outcome: 已完成。A2A 层通过 `AgentProvider` 契约按 `user_id` 获取 fake managed agent，复用与隔离语义已建立。
- Verification: `uv run python -m pytest tests/unit/test_fake_manager.py -v` 通过；`uv run python -m pytest tests/integration/test_phase3_manager_adapter.py -v` 通过；`uv run python -m pytest -v` 通过。
- Notes: 已修复两类 review finding：1) 不再在共享 executor 上重写 `self.agent`，改为每请求创建局部 `StrandsA2AExecutor`；2) 已移除测试专用 `user_id` 的硬编码耦合。

---

## Phase 4: 能力面对齐与流式转换

**User stories**: 3, 11, 12, 25, 26

### What to build

在 fake manager/fake agent 基础上补齐输入映射和输出事件翻译，使远程 A2A 调用的文本能力面尽可能接近现有用户 API。该阶段聚焦于把 A2A message 输入、agent 流式输出和最终返回语义打磨为稳定契约，并验证同一用户连续请求能命中复用语义。

### Acceptance criteria

- [x] A2A 输入会被稳定映射为内部 agent 可消费的文本输入
- [x] agent 的流式输出会被稳定翻译为 A2A 可消费的文本事件序列
- [x] 同一用户连续请求表现出与现有 API 目标一致的复用语义

### Review

- Outcome: 已完成。新增显式文本输入 mapper，将多段 A2A text parts 合并为单一内部文本 prompt；同一用户复用的 fake managed agent 现在会保留最小会话状态，并在流式文本中反映当前 turn、当前输入和上一轮输入。
- Verification: `uv run python -m pytest tests/unit/test_text_input_mapper.py -v` 通过；`uv run python -m pytest tests/integration/test_phase4_capability_alignment.py -v` 通过；`uv run python -m pytest -v` 通过，结果为 `18 passed`。
- Notes: 输出 streaming 未自定义重写，继续复用 `StrandsA2AExecutor` 的 A2A-compliant artifact streaming；旧 Phase 1 测试已从固定文案断言收敛为协议行为断言，避免与后续阶段的能力演进冲突。

### Execution status

- Worktree: 复用已存在的 Phase 4 隔离工作树 `/workspaces/skill-hub/A2A-demo/.worktree/phase-4-capability-alignment`
- Branch: `phase-4-capability-alignment`
- Ignore safety: 已确认 `.gitignore` 中的 `.worktree/` 规则生效，worktree 目录不会进入版本控制
- Environment: `uv sync` 已完成，依赖与锁文件一致
- Baseline verification: `uv run python -m pytest -v` 通过，结果为 `13 passed`

---

## Phase 5: 错误契约与并发治理

**User stories**: 16, 17, 18, 20, 22, 27

### What to build

固化失败路径和并发策略，确保第一版在认证失败、上下文缺失、manager 异常、agent 异常、客户端断连、同用户并发冲突、不同用户并行等场景下都有确定性行为。该阶段应把“同用户 busy/串行、不同用户可并行”的约束变成可验证的外部行为。

### Acceptance criteria

- [x] 主要错误场景都有统一、稳定且不泄漏内部细节的响应契约
- [x] 同一用户并发请求时系统表现为 busy 或串行化，不会触发不可控竞态
- [x] 不同用户的请求可以并行执行且不会发生上下文污染

### Review

- Outcome: 已完成。引入用户级并发守卫与统一错误映射，固化了同用户 busy、不同用户并行以及认证/manager/agent 失败路径的公共契约。
- Verification: `uv run python -m pytest tests/unit/test_user_lock.py -v` 通过；`uv run python -m pytest tests/unit/test_error_mapping.py -v` 通过；`uv run python -m pytest tests/integration/test_phase5_error_and_concurrency.py -v` 通过；`uv run python -m pytest -v` 通过，结果为 `31 passed`。
- Notes: 认证失败响应现在稳定包含 `request_id`；A2A JSON-RPC 错误统一带 `data.code` 和 `data.request_id`；同用户并发策略固定为 busy，不做内存队列。

---

## Phase 6: 接入说明与内部落地校验

**User stories**: 13, 24, 28

### What to build

编写从当前模拟实现迁移到真实内部系统的接入说明、替换步骤、边界声明和验证清单。该切片确保当前仓库中的成果不是一次性 demo，而是一套可被内部代码库采用的落地蓝图，包括哪些模块可直接迁移、哪些部分必须替换、以及内部接入后的回归验证要求。

### Acceptance criteria

- [x] 提供清晰的 fake manager 到真实 manager 的替换说明
- [x] 第一版支持边界和明确不支持的能力被完整记录
- [x] 提供面向内部系统接入时的验证清单，覆盖协议、流式、复用、并发和错误路径

### Review

- Outcome: 已完成。新增内部接入指南、验证清单和目录索引，明确哪些模块可直接迁移、哪些模块必须替换，以及内部接入后的最小验收面。
- Verification: `uv run python -m pytest -v` 通过，结果为 `31 passed`。
- Notes: 迁移文档明确将 fake manager/fake agent 定义为唯一必须替换的模拟实现；第一版能力边界与不支持项已集中收敛到接入材料中，便于内部落地时逐项验收。
