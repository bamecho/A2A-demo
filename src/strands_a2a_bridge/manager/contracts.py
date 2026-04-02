from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol


class ManagedAgent(Protocol):
    agent_id: str
    name: str
    description: str

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        ...


class AgentProvider(Protocol):
    """A2A layer only asks provider for an agent by user_id."""

    def get_or_create_agent(self, user_id: str) -> ManagedAgent:
        ...
