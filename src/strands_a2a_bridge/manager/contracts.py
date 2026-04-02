"""Agent 管理层接口定义（Protocol）."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol


class ManagedAgent(Protocol):
    """被管理的 Agent 接口，实现流式响应能力."""
    agent_id: str
    name: str
    description: str

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """流式处理用户输入并返回响应片段."""
        ...


class AgentProvider(Protocol):
    """Agent 提供者接口，按 user_id 获取或创建 Agent 实例."""

    def get_or_create_agent(self, user_id: str) -> ManagedAgent:
        """根据用户 ID 获取已存在的 Agent，或创建新的 Agent 实例."""
        ...
