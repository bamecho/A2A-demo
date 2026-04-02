"""Phase 1 测试用的 Stub Agent 实现."""

from collections.abc import AsyncIterator, Sequence
from typing import Any


class StubAgent:
    """确定性文本流式 Stub Agent，用于 Phase 1 测试验证."""

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
    """创建 StubAgent 实例."""
    return StubAgent()
