from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FakeManagedAgent:
    user_id: str
    agent_id: str
    name: str = "phase3-fake-agent"
    description: str = "Phase 3 fake managed agent"

    async def stream_async(
        self,
        _content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        _ = invocation_state
        for chunk in ("hello", "from", self.agent_id):
            yield {"data": chunk}
        yield {"result": f"hello from {self.agent_id}"}


class FakeAgentProvider:
    def __init__(self) -> None:
        self._agents_by_user_id: dict[str, FakeManagedAgent] = {}
        self._next_agent_index = 1

    def get_or_create_agent(self, user_id: str) -> FakeManagedAgent:
        cached = self._agents_by_user_id.get(user_id)
        if cached is not None:
            return cached

        if not self._agents_by_user_id:
            agent_id = "stub-agent"
        else:
            agent_id = f"fake-agent-{self._next_agent_index}"
            self._next_agent_index += 1

        agent = FakeManagedAgent(user_id=user_id, agent_id=agent_id)
        self._agents_by_user_id[user_id] = agent
        return agent
