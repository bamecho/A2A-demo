from collections.abc import AsyncIterator, Sequence
from typing import Any


class StubAgent:
    def __init__(self) -> None:
        self.name = "phase1-stub-agent"
        self.description = "Phase 1 deterministic text streaming stub agent."

    async def stream_async(
        self,
        _content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        _ = invocation_state
        for chunk in ("hello", "from", "stub-agent"):
            yield {"data": chunk}
        yield {"result": "hello from stub-agent"}


def build_stub_agent() -> StubAgent:
    return StubAgent()
