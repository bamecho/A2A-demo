"""A2A server 启动时使用的 bootstrap agent 占位实现."""

from collections.abc import AsyncIterator, Sequence
from typing import Any


class StubAgent:
    """仅用于提供基础元信息和默认 executor 占位的确定性 Stub Agent.

    当前请求处理链路会在 server 初始化后替换掉默认 executor，
    实际消息不会路由到这个 agent 执行。
    """

    def __init__(self) -> None:
        self.name = "phase1-stub-agent"
        self.description = "Phase 1 deterministic text streaming stub agent."

    async def stream_async(
        self,
        _content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """生成固定的测试响应流."""
        _ = invocation_state
        for chunk in ("hello", "from", "stub-agent"):
            yield {"data": chunk}
        yield {"result": "hello from stub-agent"}


def build_stub_agent() -> StubAgent:
    """创建 bootstrap StubAgent 实例."""
    return StubAgent()
