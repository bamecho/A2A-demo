# Validation Checklist

> Use this checklist after replacing the fake manager with the real internal manager.

## Required Checks

### 1. Protocol Path

- Check: A2A agent card can be fetched from the FastAPI-hosted route
- Success: `GET /a2a/.well-known/agent-card.json` returns `200` and streaming capability is enabled

### 2. Trusted Identity Context

- Check: `x-user-id`, `x-request-id`, `x-trace-id` flow from HTTP headers into execution context
- Success: payload metadata cannot spoof identity; missing `x-user-id` returns `401`

### 3. Same-User Reuse

- Check: two sequential requests from the same `user_id` hit the same underlying conversation/agent context
- Success: second request observes continuity rather than a fresh session

### 4. Same-User Busy

- Check: two overlapping requests from the same `user_id` are not executed concurrently
- Success: second request returns a stable busy error contract with `request_id`

### 5. Different-User Parallelism

- Check: two overlapping requests from different `user_id` values can both run
- Success: both requests succeed and their outputs/context stay isolated

### 6. Manager Failure Contract

- Check: manager/provider acquisition failure is mapped to a stable JSON-RPC error
- Success: client sees `Failed to acquire agent`, structured error code `manager_unavailable`, and `request_id`, with no traceback leakage

### 7. Agent Failure Contract

- Check: runtime failure inside the managed agent is mapped to a stable JSON-RPC error
- Success: client sees `Agent execution failed`, structured error code `agent_execution_failed`, and `request_id`, with no traceback leakage

### 8. Non-Text Rejection

- Check: file or other non-text parts are rejected before normal execution
- Success: client receives JSON-RPC `-32602` and message `Only text input parts are supported in Phase 1`

### 9. Full Regression

- Check: run the repository test suite or the equivalent internal regression suite after wiring the real provider
- Success: all existing protocol, identity, reuse, concurrency and error-path tests pass

## Suggested Command Baseline

在当前仓库中，对应的回归基线命令是：

```bash
uv run python -m pytest -v
```

内部仓库没有完全相同目录结构时，也应保留上面 1-9 条的行为验收，而不是只做 smoke test。
