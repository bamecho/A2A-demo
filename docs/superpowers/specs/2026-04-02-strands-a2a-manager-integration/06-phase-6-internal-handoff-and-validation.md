# Phase 6 Spec: 接入说明与内部落地校验

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** 将当前仓库中的模拟实现整理成可迁入真实内部系统的接入包，明确哪些模块直接复用、哪些模块必须替换，以及内部接入后的验证步骤。

**Architecture:** 保留协议层、上下文层、mapper/translator 和错误并发治理作为可迁移模块；将 fake manager/fake agent 明确标注为占位实现，并给出替换为真实内部 manager 的最小改造路径与回归清单。

**Tech Stack:** Markdown, pytest, FastAPI, Python 3.11+

---

## Scope

In scope:

- 内部接入说明
- fake 到真实 manager 的替换说明
- 支持边界文档
- 回归验证清单

Out of scope:

- 直接接入真实内部仓库
- 新增功能开发

## File plan

- Create: `docs/superpowers/specs/2026-04-02-strands-a2a-manager-integration/internal-adoption-guide.md`
- Create: `docs/superpowers/specs/2026-04-02-strands-a2a-manager-integration/validation-checklist.md`
- Modify: `docs/superpowers/specs/2026-04-02-strands-a2a-manager-integration/README.md`

## Execution tasks

### Task 1: 编写内部接入说明

- [ ] 在 `internal-adoption-guide.md` 中说明哪些模块可直接迁移
- [ ] 明确 fake manager/fake agent 是唯一必须替换的模拟部分
- [ ] 给出真实 manager 适配时的接口对齐点：`user_id`、agent 获取、stream 接口、错误边界

### Task 2: 编写验证清单

- [ ] 在 `validation-checklist.md` 中列出内部落地后的必测项
- [ ] 覆盖协议通路、身份上下文、用户复用、同用户 busy、不同用户并行、错误契约、非文本拒绝
- [ ] 每个验证项都写出最小成功标准

### Task 3: 更新目录索引

- [ ] 修改 `README.md`，加入内部迁移材料索引
- [ ] 明确目录中哪些文件用于实现，哪些文件用于迁移与验收

Verification:

- Run: `python -m pytest`
- Expected: 既有测试仍通过

## Done definition

- 真实内部仓库接入者可以只看本目录完成迁移准备
- fake 与真实替换边界足够明确
- 验收清单覆盖第一版的关键行为与明确不支持项
