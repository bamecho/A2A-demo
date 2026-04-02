# Phase 4 Spec: 能力面对齐与流式转换

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 补齐 A2A 输入映射和 agent 输出事件翻译，让远程 A2A 文本调用的行为尽量接近现有用户 API 的文本能力面。

**Architecture:** 在协议层与 fake agent 之间加入两个深模块：`A2AInputMapper` 和 `A2AEventTranslator`。前者负责把 A2A 文本输入标准化为内部输入，后者负责把内部流式事件翻译为稳定的 A2A 文本事件序列。

**Tech Stack:** Python 3.11+, pytest, FastAPI

---

## Scope

In scope:

- 文本输入映射
- 文本流事件翻译
- 连续请求复用语义的端到端验证
- mapper/translator 单元测试

Out of scope:

- 多模态 parts
- 完整工具事件透传
- 长任务状态

## File plan

- Create: `src/strands_a2a_bridge/translation/__init__.py`
- Create: `src/strands_a2a_bridge/translation/input_mapper.py`
- Create: `src/strands_a2a_bridge/translation/event_translator.py`
- Modify: `src/strands_a2a_bridge/a2a/server.py`
- Modify: `src/strands_a2a_bridge/manager/fake.py`
- Create: `tests/unit/test_input_mapper.py`
- Create: `tests/unit/test_event_translator.py`
- Create: `tests/integration/test_phase4_capability_alignment.py`

## Execution tasks

### Task 1: 输入映射模块

- [ ] 在 `src/strands_a2a_bridge/translation/input_mapper.py` 定义最小文本映射规则
- [ ] 只接受文本输入；遇到非文本 parts 时返回明确错误或拒绝
- [ ] 输出内部统一输入结构，供 fake agent 和未来真实 agent 共享

Verification:

- Run: `python -m pytest tests/unit/test_input_mapper.py -v`
- Expected: 文本输入通过，非文本输入被拒绝

### Task 2: 输出事件翻译模块

- [ ] 在 `src/strands_a2a_bridge/translation/event_translator.py` 定义文本事件翻译规则
- [ ] 将 fake agent 的内部事件统一翻译为 A2A 可消费的文本流事件
- [ ] 终态事件必须稳定，便于集成测试断言

Verification:

- Run: `python -m pytest tests/unit/test_event_translator.py -v`
- Expected: 增量文本事件和结束事件顺序稳定

### Task 3: 将 mapper/translator 接到执行链

- [ ] 修改 `src/strands_a2a_bridge/a2a/server.py`，执行链变为“读取上下文 -> 取 agent -> 输入映射 -> agent stream -> 输出翻译”
- [ ] 修改 `src/strands_a2a_bridge/manager/fake.py`，让 fake agent stream 更贴近真实文本生成行为

### Task 4: 连续请求能力面对齐测试

- [ ] 在 `tests/integration/test_phase4_capability_alignment.py` 覆盖连续两次对同一用户的文本请求
- [ ] 断言返回结果既体现文本 streaming，又体现 agent 复用语义
- [ ] 覆盖非文本输入的拒绝行为

## Done definition

- 输入映射与输出翻译是独立深模块
- 文本流式行为已稳定
- 同用户连续请求的文本能力面接近现有 API 目标
