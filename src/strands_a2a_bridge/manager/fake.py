"""Fake Agent 实现：用于 Phase 3 测试的内存级 Agent 管理."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FakeManagedAgent:
    """测试用的假 Agent，记录对话轮次和历史输入."""
    user_id: str
    agent_id: str
    name: str = "phase3-fake-agent"
    description: str = "Phase 3 fake managed agent"
    turn_count: int = 0
    last_user_input: str | None = None

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """流式返回当前轮次、输入内容和上一轮输入（用于测试验证）."""
        _ = invocation_state
        current_input = _extract_text_input(content_blocks)
        previous_input = self.last_user_input or "<none>"
        self.turn_count += 1
        self.last_user_input = current_input

        for chunk in (
            f"turn {self.turn_count}",
            f"input {current_input}",
            f"previous {previous_input}",
        ):
            yield {"data": chunk}
        yield {"result": f"turn {self.turn_count}: {current_input}"}


class FakeAgentProvider:
    """内存中的 Fake Agent 提供者，按 user_id 隔离 Agent 实例."""

    def __init__(self) -> None:
        self._agents_by_user_id: dict[str, FakeManagedAgent] = {}
        self._next_agent_index = 1

    def get_or_create_agent(self, user_id: str) -> FakeManagedAgent:
        """获取或创建与用户 ID 绑定的 FakeManagedAgent.
        
        第一个创建的 Agent 使用固定 ID "stub-agent"，后续按序号命名.
        """
        cached = self._agents_by_user_id.get(user_id)
        if cached is not None:
            return cached

        # 第一个 Agent 使用固定 ID，方便测试识别
        if not self._agents_by_user_id:
            agent_id = "stub-agent"
        else:
            agent_id = f"fake-agent-{self._next_agent_index}"
            self._next_agent_index += 1

        agent = FakeManagedAgent(user_id=user_id, agent_id=agent_id)
        self._agents_by_user_id[user_id] = agent
        return agent


def _extract_text_input(content_blocks: Sequence[Any]) -> str:
    """从 content blocks 中提取文本内容."""
    text_segments: list[str] = []
    for block in content_blocks:
        if isinstance(block, dict):
            text_value = block.get("text")
            if isinstance(text_value, str) and text_value:
                text_segments.append(text_value)
    return "\n".join(text_segments)
