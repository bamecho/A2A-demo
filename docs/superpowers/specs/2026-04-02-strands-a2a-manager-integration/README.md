# Strands A2A Manager Integration Phase Specs

> Source PRD: `docs/prd/2026-04-02-strands-a2a-manager-integration-prd.md`
> Source Plan: `plans/strands-a2a-manager-integration.md`

本目录按 phase 管理 `Strands A2A Server 与 Agent Manager 集成` 的执行级 spec。由于当前仓库无法直接接入真实内部代码，这些 spec 统一采用“可在本仓库落地的模拟实现 + 明确的内部替换缝隙”策略。

## Specs

- `01-phase-1-a2a-protocol-minimum-path.md`
- `02-phase-2-trusted-identity-context.md`
- `03-phase-3-manager-adapter-and-simulation.md`
- `04-phase-4-capability-alignment-and-stream-translation.md`
- `05-phase-5-error-contracts-and-concurrency-governance.md`
- `06-phase-6-internal-handoff-and-validation.md`

## Current Status

- Phase 1: Completed
- Phase 2: Completed
- Phase 3: Completed
- Phase 4-6: Not started

## Shared implementation shape

除非 phase spec 特别说明，统一采用以下代码布局：

- `pyproject.toml`
- `src/strands_a2a_bridge/app.py`
- `src/strands_a2a_bridge/config.py`
- `src/strands_a2a_bridge/a2a/server.py`
- `src/strands_a2a_bridge/a2a/executor.py`
- `src/strands_a2a_bridge/http/context.py`
- `src/strands_a2a_bridge/http/auth.py`
- `src/strands_a2a_bridge/manager/contracts.py`
- `src/strands_a2a_bridge/manager/fake.py`
- `src/strands_a2a_bridge/translation/input_mapper.py`
- `src/strands_a2a_bridge/translation/event_translator.py`
- `src/strands_a2a_bridge/concurrency/user_lock.py`
- `src/strands_a2a_bridge/errors.py`
- `tests/integration/`
- `tests/unit/`

## Usage

- 先从 `01` 开始，按顺序执行。
- 每个 spec 都是独立的执行说明，但默认依赖前一个 phase 已完成。
- 如果要迁入真实内部仓库，优先参考 `06-phase-6-internal-handoff-and-validation.md` 中的替换说明和验收清单。
